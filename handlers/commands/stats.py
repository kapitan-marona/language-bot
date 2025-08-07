from config.config import ADMINS

async def stats_command(update, context):
    chat_id = update.effective_chat.id
    if chat_id in ADMINS:
        await update.message.reply_text("Здесь будет статистика (например, количество сообщений, активные пользователи и т.д.)")
    else:
        await update.message.reply_text("⛔")
