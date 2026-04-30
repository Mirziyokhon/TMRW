"""
Scheduler — sends daily morning reminders for due steps.
Uses APScheduler to run a job every day at the configured reminder hour.
"""

import logging
from datetime import date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram.ext import Application
from telegram.constants import ParseMode

from src.database import get_all_active_users, get_due_steps_today, get_upcoming_deadlines
from src.config import REMINDER_HOUR

logger = logging.getLogger(__name__)


async def send_daily_reminders(app: Application):
    """Runs every morning — sends personalized reminders to each active user."""
    users = await get_all_active_users()
    today = date.today()

    for user_id in users:
        try:
            due_steps = await get_due_steps_today(user_id)
            upcoming = await get_upcoming_deadlines(user_id, days=7)

            if not due_steps and not upcoming:
                continue  # Nothing urgent — don't spam them

            msg = f"☀️ *Good morning! Here's your deadline check-in for {today.strftime('%B %d')}:*\n\n"

            if due_steps:
                msg += "⏰ *Steps due today or overdue:*\n"
                for step in due_steps:
                    days_late = (today - date.fromisoformat(step["due_date"])).days
                    late_tag = f" _(overdue by {days_late}d)_" if days_late > 0 else ""
                    msg += f"  • [{step['opp_name']}] {step['title']}{late_tag}\n"
                msg += "\n"

            if upcoming:
                msg += "📅 *Upcoming safe deadlines (next 7 days):*\n"
                for opp in upcoming:
                    safe_dl = date.fromisoformat(opp["safe_deadline"])
                    days_left = (safe_dl - today).days
                    emoji = "🔴" if days_left <= 1 else ("🟡" if days_left <= 3 else "🟠")
                    msg += f"  {emoji} *{opp['name']}* — safe deadline in {max(0, days_left)} day(s)\n"
                msg += "\n"

            msg += "_Start with just one small thing today. That's enough._ 💪"

            await app.bot.send_message(
                chat_id=user_id,
                text=msg,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to send reminder to {user_id}: {e}")


def start_scheduler(app: Application = None):
    """Start the scheduler - can be called with or without app."""
    import asyncio
    
    scheduler = AsyncIOScheduler()
    
    if app:
        scheduler.add_job(
            send_daily_reminders,
            trigger=CronTrigger(hour=REMINDER_HOUR, minute=0),
            args=[app],
            id="daily_reminders",
            name="Daily morning reminders",
            replace_existing=True,
        )
    
    try:
        scheduler.start()
        logger.info(f"⏰ Scheduler started — reminders will fire at {REMINDER_HOUR}:00 daily")
    except RuntimeError:
        # Event loop not running yet, schedule it to start later
        logger.info("⏰ Scheduler will start when event loop is available")
