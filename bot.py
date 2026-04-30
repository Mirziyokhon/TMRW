"""
DeadlineBot - Telegram bot that helps you never miss opportunities.
Accepts voice/text messages, extracts opportunity info, searches the web,
generates mini-steps, and sends smart reminders.
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters,
)
from src.config import BOT_TOKEN
from src.handlers import (
    start_handler, voice_handler, text_handler,
    list_handler, callback_handler, help_handler,
)
from src.scheduler import start_scheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("list", list_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))

    start_scheduler(app)

    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    await asyncio.Event().wait()  # run forever

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
