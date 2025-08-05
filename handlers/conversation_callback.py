from telegram import Update
from telegram.ext import ContextTypes
from state.session import user_sessions
from .conversation import (
    interface_language_callback,
    target_language_callback,
    level_callback,
    style_callback,
)


# Этот handler просто делегирует на основной обработчик колбеков
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("interface_lang:"):
        await interface_language_callback(update, context)
    elif data.startswith("target_lang:"):
        await target_language_callback(update, context)
    elif data.startswith("level:"):
        await level_callback(update, context)
    elif data.startswith("style:"):
        await style_callback(update, context)
    # ...можно добавить другие ветки по мере необходимости

