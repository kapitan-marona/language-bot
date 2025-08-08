import logging
from telegram import Update
from telegram.error import BadRequest, TimedOut, NetworkError
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Unhandled exception in handler", exc_info=context.error)

    try:
        chat_id = None
        if isinstance(update, Update):
            if update.effective_chat:
                chat_id = update.effective_chat.id
            elif update.callback_query and update.callback_query.message:
                chat_id = update.callback_query.message.chat_id

        if chat_id:
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Что-то пошло не так. Я уже пробую ещё раз!"
            )
    except (BadRequest, TimedOut, NetworkError) as e:
        logger.warning("Failed to notify user about error: %s", e)
