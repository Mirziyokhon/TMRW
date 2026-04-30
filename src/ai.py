"""
AI layer — handles:
1. Voice transcription via Groq Whisper
2. Opportunity extraction + step generation via Google Gemini
3. Web search via DuckDuckGo scraping to enrich/verify opportunity details
"""

import os
import json
import httpx
import base64
import asyncio
from datetime import date, timedelta
from src.config import GEMINI_API_KEY, GROQ_API_KEY, SAFE_DAY_BUFFER

# Groq and Gemini clients
groq_headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
gemini_headers = {"Content-Type": "application/json"}


# ─── 1. TRANSCRIPTION ────────────────────────────────────────────────────────

async def transcribe_voice(file_path: str) -> str:
    """Transcribe a voice message using Groq Whisper."""
    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as audio_file:
            files = {"file": ("audio.ogg", audio_file, "audio/ogg")}
            data = {"model": "whisper-large-v3"}
            
            response = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers=groq_headers,
                files=files,
                data=data
            )
            response.raise_for_status()
            result = response.json()
            return result.get("text", "")


# ─── 2. OPPORTUNITY EXTRACTION ───────────────────────────────────────────────

EXTRACTION_SYSTEM = """Extract opportunity info as JSON only:
{
  "name": "opportunity name",
  "description": "brief description", 
  "category": "scholarship|program|competition|college|other",
  "real_deadline": "YYYY-MM-DD or null",
  "requirements": ["req1", "req2"],
  "search_query": "search terms to find official page"
}

Today: {today}"""


async def extract_opportunity(text: str) -> dict:
    """Use Google Gemini to extract structured opportunity data from user text."""
    today = date.today().isoformat()
    system = EXTRACTION_SYSTEM.replace("{today}", today)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
            headers=gemini_headers,
            json={
                "contents": [{
                    "parts": [
                        {"text": f"System: {system}\n\nUser: {text}"}
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1000
                }
            }
        )
        response.raise_for_status()
        result = response.json()
        
        # Extract the text from Gemini response
        raw = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())


# ─── 3. WEB SEARCH ───────────────────────────────────────────────────────────

async def call_gemini_with_retry(client, prompt, max_retries=3):
    """Call Gemini API with retry logic for 503 errors."""
    for attempt in range(max_retries):
        try:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
                headers=gemini_headers,
                json={
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 1500
                    }
                }
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503 and attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise
    return None


async def search_web(query: str) -> dict:
    """Use DuckDuckGo scraping to find official info about an opportunity."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Use DuckDuckGo HTML results
        response = await client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        response.raise_for_status()
        
        # Simple extraction of first few results (basic scraping)
        html_content = response.text
        
        # Use Gemini to parse the search results and extract structured info
        parse_prompt = f"""Based on these search results for "{query}", extract information about the opportunity and return a JSON object with:
{{
  "name": "official name",
  "url": "official application URL",
  "real_deadline": "YYYY-MM-DD",
  "description": "what this opportunity is",
  "requirements": ["requirement 1", "requirement 2", ...],
  "extra_notes": "any other important info"
}}

Search results snippet:
{html_content[:2000]}  # Limit to avoid token limits

Return ONLY the JSON, no markdown."""
        
        try:
            gemini_response = await call_gemini_with_retry(client, parse_prompt)
            
            if not gemini_response:
                print("Web search: Gemini unavailable, returning empty result")
                return {}
                
            result = gemini_response.json()
            raw = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())
        except Exception as e:
            print(f"Web search parsing error: {e}")
            return {}  # Web search result couldn't be parsed — not fatal


# ─── 4. STEP GENERATION ──────────────────────────────────────────────────────

STEPS_SYSTEM = """You are a productivity coach helping someone apply for an opportunity before its deadline.
Given the opportunity details and the real deadline, generate a realistic list of mini-steps to complete the application.

Rules:
- Steps should start AT LEAST 3 weeks before the deadline (or from today if less time)
- Each step should be concrete and completable in 1-2 hours max
- Space them out realistically — don't cluster everything at the end
- The last step should always be "Final review & submit" scheduled 2 days before the safe deadline
- Return ONLY a valid JSON array of steps, no markdown:

[
  {"title": "step title", "due_date": "YYYY-MM-DD"},
  ...
]

Today is {today}. Safe deadline is {safe_deadline}. Real deadline is {real_deadline}."""


async def generate_steps(opportunity: dict, real_deadline: str, safe_deadline: str) -> list:
    """Generate mini-steps for an opportunity."""
    today = date.today().isoformat()
    system = STEPS_SYSTEM.replace("{today}", today) \
                          .replace("{safe_deadline}", safe_deadline) \
                          .replace("{real_deadline}", real_deadline)

    prompt = f"""Opportunity: {opportunity.get('name', 'Unknown')}
Description: {opportunity.get('description', '')}
Requirements: {json.dumps(opportunity.get('requirements', []))}
Category: {opportunity.get('category', 'general')}

Generate the mini-steps."""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
                headers=gemini_headers,
                json={
                    "contents": [{
                        "parts": [
                            {"text": f"System: {system}\n\nUser: {prompt}"}
                        ]
                    }],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 1000
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract the text from Gemini response
            raw = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())
    except Exception as e:
        print(f"Step generation error: {e}")
        # Return basic steps if generation fails
        return [
            {"title": "Research the opportunity", "due_date": today},
            {"title": "Start application", "due_date": safe_deadline}
        ]


# ─── 5. MASTER PIPELINE ──────────────────────────────────────────────────────

async def process_opportunity_input(text: str) -> dict | None:
    """
    Full pipeline: text → extract → web search → generate steps → return structured data.
    Returns None if extraction fails.
    """
    # Step 1: Extract from user text
    extracted = await extract_opportunity(text)
    if not extracted or not extracted.get("name"):
        return None

    # Step 2: Search web to enrich/verify
    web_data = {}
    if extracted.get("search_query"):
        web_data = await search_web(extracted["search_query"])

    # Step 3: Merge — prefer web data for deadline/URL, user text for intent
    name = web_data.get("name") or extracted.get("name", "Unknown Opportunity")
    description = web_data.get("description") or extracted.get("description", "")
    url = web_data.get("url", "")
    category = extracted.get("category", "other")
    requirements = list(set(
        extracted.get("requirements", []) + web_data.get("requirements", [])
    ))

    # Determine real deadline
    real_deadline_str = (
        web_data.get("real_deadline") or
        extracted.get("real_deadline")
    )

    if not real_deadline_str:
        return {"name": name, "description": description, "url": url,
                "category": category, "error": "no_deadline"}

    try:
        real_deadline = date.fromisoformat(real_deadline_str)
    except ValueError:
        return {"name": name, "error": "bad_deadline"}

    safe_deadline = real_deadline - timedelta(days=SAFE_DAY_BUFFER)
    if safe_deadline < date.today():
        safe_deadline = date.today()

    merged = {
        "name": name,
        "description": description,
        "url": url,
        "category": category,
        "requirements": requirements,
        "extra_notes": web_data.get("extra_notes", ""),
    }

    # Step 4: Generate mini-steps
    steps = await generate_steps(merged, real_deadline.isoformat(), safe_deadline.isoformat())

    return {
        "name": name,
        "description": description,
        "url": url,
        "category": category,
        "real_deadline": real_deadline.isoformat(),
        "safe_deadline": safe_deadline.isoformat(),
        "steps": steps,
        "raw_input": text,
    }
