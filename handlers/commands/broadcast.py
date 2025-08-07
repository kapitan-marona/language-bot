from telegram import Update
from telegram.ext import ContextTypes
from config.config import ADMINS
from state.session import user_sessions

async def broadcast_command(update, context):
    chat_id = update.effective_chat.id
    if chat_id in ADMINS:
        if context.args:
            text = " ".join(context.args)
            count = 0
            for uid in user_sessions:
                try:
                    await context.bot.send_message(chat_id=uid, text=text)
                    count += 1
                except Exception:
                    continue
            await update.message.reply_text(f"Сообщение отправлено {count} пользователям.")
        else:
            await update.message.reply_text("Введите текст после команды. Пример: /broadcast Привет всем!")
    else:
        await update.message.reply_text("⛔️")
