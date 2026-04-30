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

def check_env_vars():
    """Check if all required environment variables are set."""
    missing = []
    if not BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("Please set these in your Render dashboard Environment tab.")
        return False
    return True

# Only check if running directly (not when imported)
if __name__ == "__main__":
    check_env_vars()
