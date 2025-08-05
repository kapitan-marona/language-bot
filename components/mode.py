from telegram import InlineKeyboardButton, InlineKeyboardMarkup

MODE_SWITCH_MESSAGES = {
    "voice": {
        "en": "🔊 Ok. I'm all ears!",
        "ru": "🔊 Ок. Отвечу аудиосообщением!"
    },
    "text": {
        "en": "⌨️ Ok. Text me!",
        "ru": "⌨️ Ок. Буду печатать!"
    }
}


def get_mode_keyboard(current_mode, lang):
    if current_mode == "voice":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "⌨️ Вернуться к тексту" if lang == "ru" else "⌨️ Switch to text",
                callback_data="mode:text"
            )]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔊 Вернуться к аудио" if lang == "ru" else "🔊 Switch to voice",
                callback_data="mode:voice"
            )]
        ])

