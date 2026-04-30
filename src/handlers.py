"""
Telegram handlers — all the bot's responses to user actions.
"""

import os
import tempfile
import logging
from datetime import date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from src.database import (
    init_db, upsert_user, save_opportunity,
    get_opportunities, get_opportunity, get_steps,
    mark_step_done, mark_opportunity_done,
    update_opportunity
)
from src.ai import transcribe_voice, process_opportunity_input

logger = logging.getLogger(__name__)

# Emoji map for categories
CATEGORY_EMOJI = {
    "scholarship": "🎓",
    "program": "🏫",
    "competition": "🏆",
    "college": "🏛️",
    "other": "📌",
    "general": "📌",
}


# ─── /start ──────────────────────────────────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await init_db()
    user = update.effective_user
    await upsert_user(user.id, user.username or user.first_name)

    await update.message.reply_text(
        f"Hey {user.first_name}! 👋\n\n"
        "I'm your *DeadlineBot* — I'll make sure you never miss an opportunity again.\n\n"
        "📣 *How to use me:*\n"
        "Just send me a *voice message* or *text* describing any opportunity you found "
        "(scholarship, summer program, competition, etc.) and I'll:\n\n"
        "✅ Extract the details\n"
        "🔍 Search the web to verify & enrich them\n"
        "📅 Generate a step-by-step plan with mini-deadlines\n"
        "⏰ Remind you every day when a step is due\n\n"
        "Try it now — tell me about an opportunity!\n\n"
        "Commands: /list — see all your opportunities | /help",
        parse_mode="Markdown"
    )


# ─── /help ───────────────────────────────────────────────────────────────────

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*DeadlineBot Help* 🤖\n\n"
        "*Adding an opportunity:*\n"
        "Just send a voice note or text message describing it. Include the name and deadline if you know it.\n\n"
        "*Commands:*\n"
        "/list — view all active opportunities\n"
        "/help — this message\n\n"
        "*Tips:*\n"
        "• You can say things like _'Stanford OHS summer program, deadline June 15'_\n"
        "• Or just the name — I'll search the web for the deadline\n"
        "• Every morning at 9am I'll remind you what's due today",
        parse_mode="Markdown"
    )


# ─── VOICE MESSAGE ───────────────────────────────────────────────────────────

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙️ Got your voice message! Transcribing...")
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    # Download voice file
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        await file.download_to_drive(tmp.name)
        tmp_path = tmp.name

    try:
        transcript = await transcribe_voice(tmp_path)
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        await update.message.reply_text("❌ Couldn't transcribe your voice message. Try again or send text.")
        return
    finally:
        os.unlink(tmp_path)

    await update.message.reply_text(f"📝 *Heard:* _{transcript}_\n\nNow analyzing...", parse_mode="Markdown")
    await process_and_reply(update, context, transcript)


# ─── TEXT MESSAGE ────────────────────────────────────────────────────────────

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        return

    # Check if this is a response to an edit request
    if "pending_edit" in context.user_data:
        edit_data = context.user_data["pending_edit"]
        opp_id = edit_data["opp_id"]
        field = edit_data["field"]
        
        try:
            # Validate deadline format
            if field == "deadline":
                date.fromisoformat(text)  # Will raise ValueError if invalid format
            
            await update_opportunity(opp_id, field, text)
            await update.message.reply_text(f"✅ *{field.title()} updated successfully!*", parse_mode="Markdown")
            
            # Clear the pending edit
            del context.user_data["pending_edit"]
            
        except ValueError:
            await update.message.reply_text("❌ Invalid date format. Please use YYYY-MM-DD format.")
        except Exception as e:
            logger.error(f"Update failed: {e}")
            await update.message.reply_text("❌ Failed to update. Please try again.")
        
        return

    await update.message.reply_text("🔍 Analyzing your opportunity and searching the web...")
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    await process_and_reply(update, context, text)


# ─── SHARED PROCESSING ───────────────────────────────────────────────────────

async def process_and_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user_id = update.effective_user.id

    try:
        result = await process_opportunity_input(text)
    except Exception as e:
        logger.error(f"AI processing failed: {e}")
        await update.message.reply_text("❌ Something went wrong analyzing that. Try again!")
        return

    if not result:
        await update.message.reply_text(
            "🤔 I couldn't extract an opportunity from that.\n"
            "Try: _'Stanford summer program for high schoolers, deadline June 15'_",
            parse_mode="Markdown"
        )
        return

    if result.get("error") == "no_deadline":
        await update.message.reply_text(
            f"✅ Found: *{result['name']}*\n\n"
            "⚠️ But I couldn't find a deadline. What's the deadline date?",
            parse_mode="Markdown"
        )
        return

    if result.get("error") == "bad_deadline":
        await update.message.reply_text("❌ The deadline date didn't parse correctly. Try mentioning it clearly, like 'deadline June 15 2025'.")
        return

    # Save to DB
    opp_id = await save_opportunity(user_id, result)

    # Build confirmation message
    emoji = CATEGORY_EMOJI.get(result.get("category", "other"), "📌")
    steps = result.get("steps", [])
    today = date.today()

    steps_text = ""
    for i, step in enumerate(steps):
        due = date.fromisoformat(step["due_date"])
        days_left = (due - today).days
        prefix = "🔴" if days_left < 0 else ("🟡" if days_left <= 3 else "🟢")
        steps_text += f"  {prefix} {step['due_date']} — {step['title']}\n"

    url_line = f"\n🔗 {result['url']}" if result.get("url") else ""
    desc_line = f"\n_{result['description']}_" if result.get("description") else ""

    msg = (
        f"{emoji} *{result['name']}*{desc_line}{url_line}\n\n"
        f"📅 Real deadline: *{result['real_deadline']}*\n"
        f"⚠️ Your safe deadline: *{result['safe_deadline']}* _(submit by this date!)_\n\n"
        f"📋 *Your plan:*\n{steps_text}\n"
        f"I'll remind you each morning when a step is due. You got this! 💪"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Looks good!", callback_data=f"confirm:{opp_id}")],
        [InlineKeyboardButton("✏️ Edit details", callback_data=f"edit:{opp_id}")],
        [InlineKeyboardButton("🗑️ Delete this", callback_data=f"delete:{opp_id}")]
    ]

    await update.message.reply_text(
        msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─── /list ───────────────────────────────────────────────────────────────────

async def list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    opportunities = await get_opportunities(user_id)

    if not opportunities:
        await update.message.reply_text(
            "You have no active opportunities yet.\n"
            "Send me a voice note or text to add one! 🎯"
        )
        return

    today = date.today()
    msg = "📋 *Your Active Opportunities:*\n\n"

    for opp in opportunities:
        emoji = CATEGORY_EMOJI.get(opp.get("category", "other"), "📌")
        real_dl = date.fromisoformat(opp["real_deadline"])
        safe_dl = date.fromisoformat(opp["safe_deadline"])
        days_to_safe = (safe_dl - today).days

        if days_to_safe < 0:
            urgency = "🔴 OVERDUE safe deadline!"
        elif days_to_safe <= 3:
            urgency = f"🟡 Safe deadline in {days_to_safe}d"
        elif days_to_safe <= 7:
            urgency = f"🟠 {days_to_safe} days to safe deadline"
        else:
            urgency = f"🟢 {days_to_safe} days left"

        steps = await get_steps(opp["id"])
        done = sum(1 for s in steps if s["done"])
        total = len(steps)
        progress = f"{done}/{total} steps done"

        msg += f"{emoji} *{opp['name']}*\n"
        msg += f"   {urgency} | {progress}\n"
        msg += f"   Real deadline: {opp['real_deadline']}\n\n"

    # Add management buttons
    keyboard = []
    for opp in opportunities:
        emoji = CATEGORY_EMOJI.get(opp.get("category", "other"), "📌")
        keyboard.append([
            InlineKeyboardButton(f"{emoji} {opp['name']}", callback_data=f"manage:{opp['id']}")
        ])
    
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


# ─── CALLBACK BUTTONS ────────────────────────────────────────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    action, opp_id = data.split(":")
    opp_id = int(opp_id)

    if action == "confirm":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("✅ Saved! I'll remind you each morning when a step is due.")

    elif action == "manage":
        # Get opportunity details and show management options
        opp = await get_opportunity(opp_id)
        if not opp:
            await query.edit_message_text("❌ Opportunity not found.")
            return
        
        # Verify user owns this opportunity
        if opp["user_id"] != update.effective_user.id:
            await query.edit_message_text("❌ You don't have permission to manage this opportunity.")
            return
        
        emoji = CATEGORY_EMOJI.get(opp.get("category", "other"), "📌")
        steps = await get_steps(opp_id)
        done = sum(1 for s in steps if s["done"])
        total = len(steps)
        
        # Show opportunity details with management options
        url_line = f"\n🔗 {opp['url']}" if opp.get("url") else ""
        desc_line = f"\n_{opp['description']}_" if opp.get("description") else ""
        
        msg = (
            f"{emoji} *{opp['name']}*{desc_line}{url_line}\n\n"
            f"📅 Real deadline: *{opp['real_deadline']}*\n"
            f"⚠️ Safe deadline: *{opp['safe_deadline']}*\n"
            f"📊 Progress: {done}/{total} steps done\n\n"
            f"*What would you like to do?*"
        )
        
        keyboard = [
            [InlineKeyboardButton("📝 Edit name", callback_data=f"edit_name:{opp_id}")],
            [InlineKeyboardButton("📄 Edit description", callback_data=f"edit_desc:{opp_id}")],
            [InlineKeyboardButton("🔗 Edit URL", callback_data=f"edit_url:{opp_id}")],
            [InlineKeyboardButton("📅 Edit deadline", callback_data=f"edit_deadline:{opp_id}")],
            [InlineKeyboardButton("🗑️ Delete opportunity", callback_data=f"delete:{opp_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_manage:{opp_id}")]
        ]
        
        await query.edit_message_text(
            msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif action == "cancel_manage":
        await query.edit_message_text("❌ Management cancelled.")

    elif action == "edit":
        await query.edit_message_reply_markup(reply_markup=None)
        
        # Show edit options
        keyboard = [
            [InlineKeyboardButton("📝 Edit name", callback_data=f"edit_name:{opp_id}")],
            [InlineKeyboardButton("📄 Edit description", callback_data=f"edit_desc:{opp_id}")],
            [InlineKeyboardButton("🔗 Edit URL", callback_data=f"edit_url:{opp_id}")],
            [InlineKeyboardButton("📅 Edit deadline", callback_data=f"edit_deadline:{opp_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_edit:{opp_id}")]
        ]
        
        await query.message.reply_text(
            "✏️ *What would you like to edit?*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif action == "edit_name":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "📝 *Send me the new name for this opportunity:*",
            parse_mode="Markdown"
        )
        # Store context for next message
        context.user_data["pending_edit"] = {"opp_id": opp_id, "field": "name"}

    elif action == "edit_desc":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "📄 *Send me the new description:*",
            parse_mode="Markdown"
        )
        context.user_data["pending_edit"] = {"opp_id": opp_id, "field": "description"}

    elif action == "edit_url":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "🔗 *Send me the new URL:*",
            parse_mode="Markdown"
        )
        context.user_data["pending_edit"] = {"opp_id": opp_id, "field": "url"}

    elif action == "edit_deadline":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "📅 *Send me the new deadline (YYYY-MM-DD format):*",
            parse_mode="Markdown"
        )
        context.user_data["pending_edit"] = {"opp_id": opp_id, "field": "deadline"}

    elif action == "cancel_edit":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("❌ Edit cancelled.")

    elif action == "delete":
        await mark_opportunity_done(opp_id)
        await query.edit_message_text("🗑️ Deleted.")

    elif action == "step_done":
        await mark_step_done(opp_id)  # here opp_id is actually step_id
        await query.edit_message_text("✅ Step marked as done! Keep going 🔥")
