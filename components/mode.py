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


def get_mode_keyboard(current_mode: str, lang_code="ru"):
    """
    current_mode: "voice" или "text"
    lang_code: "ru" или "en"
    """
    if current_mode == "voice":
        # Кнопка для возврата к тексту
        button_text = "⌨️ Вернуться к тексту" if lang_code == "ru" else "⌨️ Switch to text"
        callback_data = "mode:text"
    else:
        button_text = "🔊 Вернуться к аудио" if lang_code == "ru" else "🔊 Switch to voice"
        callback_data = "mode:voice"

    keyboard = [
        [InlineKeyboardButton(button_text, callback_data=callback_data)]
    ]
    return InlineKeyboardMarkup(keyboard)

