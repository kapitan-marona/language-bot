from config import ADMINS

async def promo_command(update, context):
    chat_id = update.effective_chat.id
    if chat_id in ADMINS:
        await update.message.reply_text("Промокоды: (тут будет логика работы с промокодами)")
    else:
        await update.message.reply_text("⛔️")
