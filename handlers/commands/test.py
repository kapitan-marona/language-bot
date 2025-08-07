from telegram import Update
from telegram.ext import ContextTypes
from config.config import ADMINS

async def test_command(update, context):
    chat_id = update.effective_chat.id
    if chat_id in ADMINS:
        await update.message.reply_text("✅ Тестовая команда работает!")
    else:
        await update.message.reply_text("⛔")
