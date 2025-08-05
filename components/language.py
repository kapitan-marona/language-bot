from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Все поддерживаемые языки (можно расширять)
LANGUAGES = {
    "en": "English 🇬🇧",
    "es": "Español 🇪🇸",
    "de": "Deutsch 🇩🇪",
    "fr": "Français 🇫🇷",
    "sv": "Svenska 🇸🇪",
    "fi": "Suomi 🇫🇮",
    "ru": "Русский 🇷🇺",
}

# Текст для запроса языка
TARGET_LANG_PROMPT = {
    "ru": "🌍 Выбери язык для изучения:",
    "en": "🌍 Choose a language to learn:"
}

def get_target_language_keyboard(lang_code="en"):
    """
    Возвращает InlineKeyboardMarkup с поддерживаемыми языками.
    """
    buttons = []
    row = []
    for code, label in LANGUAGES.items():
        row.append(InlineKeyboardButton(label, callback_data=f"target_{code}"))
        # Делаем по две кнопки в ряд
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)
