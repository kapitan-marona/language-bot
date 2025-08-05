from telegram import InlineKeyboardButton, InlineKeyboardMarkup

MODE_SWITCH_MESSAGES = {
    "voice": {
        "en": "🔊 Switched to voice mode. Send me an audio message!",
        "ru": "🔊 Готов слушать твои аудиосообщения!"
    },
    "text": {
        "en": "⌨️ Switched to text mode. Send me a text!",
        "ru": "⌨️ Теперь можно писать текстом!"
    }
}


def get_mode_keyboard(current_mode="text", lang_code="en"):
    """
    Клавиатура для выбора режима общения (voice/text).
    """
    if current_mode == "voice":
        button = InlineKeyboardButton(
            "⌨️ Текст / Text", callback_data="mode:text"
        )
    else:
        button = InlineKeyboardButton(
            "🔊 Голос / Voice", callback_data="mode:voice"
        )
    return InlineKeyboardMarkup([[button]])
