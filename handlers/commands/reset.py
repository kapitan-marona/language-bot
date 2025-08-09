from telegram import Update
from telegram.ext import ContextTypes
from config.config import ADMINS
from state.session import user_sessions
from components.profile_db import clear_user_profile  # NEW: reset DB profile

async def reset_command(update, context):
    chat_id = update.effective_chat.id
    if chat_id in ADMINS:
        user_sessions[chat_id] = {}  # keep: reset in-memory session
        try:
            context.user_data.clear()  # NEW: clear user_data cache
        except Exception:
            pass
        clear_user_profile(chat_id)   # NEW: clear DB profile
        await update.message.reply_text("Сброс выполнен. Настройки очищены.")
    else:
        await update.message.reply_text("⛔️")
