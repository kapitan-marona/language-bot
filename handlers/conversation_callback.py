from telegram import Update
from telegram.ext import ContextTypes
from state.session import user_sessions
from .conversation import conversation_callback  # импортируй основной handler

# Этот handler просто делегирует на основной обработчик колбеков
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await conversation_callback(update, context)
