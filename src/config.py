"""
Configuration — load secrets from environment variables.
Create a .env file in the project root with these keys.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# How many days before the real deadline to set the "Last Safe Day"
SAFE_DAY_BUFFER = 5

# What hour (24h) to send daily reminders
REMINDER_HOUR = 9  # 9:00 AM

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in .env")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in .env")
