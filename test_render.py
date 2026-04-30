#!/usr/bin/env python3
"""Simple test script to debug Render deployment issues."""

import os
print("🔍 Debugging Render deployment...")

# Check environment variables
env_vars = {
    'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
    'GROQ_API_KEY': os.getenv('GROQ_API_KEY'), 
    'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
    'SAFE_DAY_BUFFER': os.getenv('SAFE_DAY_BUFFER'),
    'REMINDER_HOUR': os.getenv('REMINDER_HOUR')
}

print("\n📋 Environment Variables:")
for key, value in env_vars.items():
    if value:
        masked = value[:8] + "..." if len(value) > 8 else "***"
        print(f"✅ {key}: {masked}")
    else:
        print(f"❌ {key}: NOT SET")

# Test imports
print("\n📦 Testing imports...")
try:
    import asyncio
    print("✅ asyncio")
except ImportError as e:
    print(f"❌ asyncio: {e}")

try:
    from telegram import Update
    print("✅ telegram")
except ImportError as e:
    print(f"❌ telegram: {e}")

try:
    from src.config import BOT_TOKEN
    print("✅ src.config")
except ImportError as e:
    print(f"❌ src.config: {e}")

print("\n🎯 If all imports work but env vars are missing, add them in Render dashboard!")
