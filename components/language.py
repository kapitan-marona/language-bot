from telegram import InlineKeyboardButton, InlineKeyboardMarkup 

SUPPORTED_LANGUAGES = {
    "en": "English",
    "ru": "Русский",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "sv": "Svenska",
    "fi": "Suomi"
}

# Список доступных языков для изучения
TARGET_LANGUAGES = {
    "en": "🇬🇧 English",
    "ru": "🇷🇺 Русский",
    "es": "🇪🇸 Español",
    "fr": "🇫🇷 Français",
    "de": "🇩🇪 Deutsch",
    "sv": "🇸🇪 Svenska",
    "fi": "🇫🇮 Suomi"
}

# Тексты-приглашения выбрать изучаемый язык
TARGET_LANG_PROMPT = {
    "ru": "Какой язык ты хочешь изучать? 🌍",
    "en": "Which language do you want to learn? 🌍",
}

# Генерация inline-кнопок для выбора target language
def get_target_language_keyboard(lang_code: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"target_{code}")]
        for code, label in TARGET_LANGUAGES.items() if code != lang_code
    ]
    return InlineKeyboardMarkup(keyboard)

