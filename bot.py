"""
DeadlineBot - Telegram bot that helps you never miss opportunities.
Accepts voice/text messages, extracts opportunity info, searches the web,
generates mini-steps, and sends smart reminders.
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from src.handlers import (
    start_handler,
    voice_handler,
    text_handler,
    list_handler,
    callback_handler,
    help_handler,
)
from src.scheduler import start_scheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to run the bot."""
    from src.config import BOT_TOKEN, check_env_vars
    
    # Check environment variables first
    if not check_env_vars():
        return
    
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("list", list_handler))
    app.add_handler(CommandHandler("help", help_handler))

    # Messages
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # Inline button callbacks
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Start the daily reminder scheduler
    start_scheduler(app)

    logger.info("🤖 DeadlineBot is running...")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)


def run_bot():
    """Entry point for Render."""
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
        # If we get here, there's already a running loop
        loop.create_task(main())
        loop.run_forever()
    except RuntimeError:
        # No running loop, create a new one
        asyncio.run(main())


if __name__ == "__main__":
    run_bot()
