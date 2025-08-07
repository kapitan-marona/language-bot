from config import ADMINS
from state.session import user_sessions

async def reset_command(update, context):
    chat_id = update.effective_chat.id
    if chat_id in ADMINS:
        user_sessions[chat_id] = {}  # Сброс всей сессии
        await update.message.reply_text("Сессия сброшена. Начни заново.")
    else:
        await update.message.reply_text("⛔️")
