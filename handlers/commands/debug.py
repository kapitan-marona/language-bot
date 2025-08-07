from config.config import ADMINS
from state.session import user_sessions
import json

async def session_command(update, context):
    chat_id = update.effective_chat.id
    if chat_id in ADMINS:
        session = user_sessions.get(chat_id, {})
        await update.message.reply_text(f"Твоя сессия:\n{json.dumps(session, ensure_ascii=False, indent=2)}")
    else:
        await update.message.reply_text("⛔️")
