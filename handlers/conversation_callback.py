from telegram import Update
from telegram.ext import ContextTypes
from components.onboarding import (
    interface_language_callback,
    onboarding_ok_callback,
    target_language_callback,
    level_callback,
    level_guide_callback,
    close_level_guide_callback,
    style_callback,
)
from handlers.mode import get_mode_keyboard
from state.session import user_sessions

# безопасность и логирование
import logging
from utils.decorators import safe_handler

logger = logging.getLogger(__name__)


def _parse_callback_value(data: str, expected_prefix: str) -> str | None:
    """
    Безопасно извлекает значение из callback_data формата '<prefix>:<value>'.
    Возвращает None, если формат некорректен или префикс не совпадает.
    """
    if not data or ":" not in data:
        return None
    prefix, value = data.split(":", 1)
    if prefix != expected_prefix:
        return None
    value = (value or "").strip()
    return value or None


@safe_handler
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""

    # Роутинг по префиксам/значениям
    if data.startswith("interface_lang:"):
        await interface_language_callback(update, context)
        return

    if data == "onboarding_ok":
        await onboarding_ok_callback(update, context)
        return

    if data.startswith("target_lang:"):
        await target_language_callback(update, context)
        return

    if data.startswith("level:"):
        await level_callback(update, context)
        return

    if data == "level_guide":
        await level_guide_callback(update, context)
        return

    if data == "close_level_guide":
        await close_level_guide_callback(update, context)
        return

    if data.startswith("style:"):
        await style_callback(update, context)
        return

    # Переключение режима ответа (voice/text)
    if data in ("mode:voice", "mode:text"):
        chat_id = query.message.chat_id
        session = user_sessions.setdefault(chat_id, {})
        interface_lang = session.get("interface_lang", "ru")

        new_mode = _parse_callback_value(data, "mode")
        if new_mode not in ("voice", "text"):
            logger.warning("Unknown mode value in callback: %r", data)
            new_mode = "text"

        session["mode"] = new_mode

        await query.edit_message_text(
            text=("🔊 Теперь отвечаю голосом" if interface_lang == "ru" else "🔊 Now I'll reply with voice")
            if new_mode == "voice"
            else ("⌨️ Теперь отвечаю текстом" if interface_lang == "ru" else "⌨️ Now I'll reply with text"),
            reply_markup=get_mode_keyboard(new_mode, interface_lang),
        )
        return

    # Если дошли сюда — неизвестный callback_data
    logger.warning("Unhandled callback_data: %r", data)
    # Мягко отвечаем, чтобы убрать "loading" на кнопке
    try:
        await query.answer()
    except Exception:
        # на всякий не валим обработчик
        logger.debug("Failed to answer callback for unknown data")
