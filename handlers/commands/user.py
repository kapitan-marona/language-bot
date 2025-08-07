from config import ADMINS
from state.session import user_sessions

async def users_command(update, context):
    chat_id = update.effective_chat.id
    if chat_id in ADMINS:
        count = len(user_sessions)
        await update.message.reply_text(f"В системе {count} пользователей.")
    else:
        await update.message.reply_text("⛔️")

async def user_command(update, context):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    session["is_admin"] = False
    await update.message.reply_text("Теперь ты обычный пользователь.")
