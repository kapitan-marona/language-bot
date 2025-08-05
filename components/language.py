from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Языки для изучения (и их флаги)
LANGUAGES = {
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "fr": "🇫🇷 Français",
    "es": "🇪🇸 Español",
    "de": "🇩🇪 Deutsch",
    "sv": "🇸🇪 Svenska",
    "fi": "🇫🇮 Suomi"
}

TARGET_LANG_PROMPT = {
    "ru": "🌍 Выбери язык для изучения:",
    "en": "🌍 Choose a language to learn:"
}

def get_target_language_keyboard():
    """
    Возвращает InlineKeyboardMarkup с поддерживаемыми языками (по 2 в ряд).
    """
    buttons = []
    row = []
    for code, label in LANGUAGES.items():
        row.append(InlineKeyboardButton(label, callback_data=f"target_lang:{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)
