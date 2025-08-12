from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from state.session import user_sessions
from components.onboarding import send_onboarding

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # Полный сброс in-memory сессии
    user_sessions.pop(chat_id, None)
    # Сообщение-подтверждение
    await update.message.reply_text("🔄 Сессию очистил. Запускаю онбординг заново.")
    # Запуск онбординга
    await send_onboarding(update, context)
