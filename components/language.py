from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Список доступных языков для изучения
TARGET_LANGUAGES = {
    "en": "🇬🇧 English",
    "ru": "🇷🇺 Русский",
    "es": "🇪🇸 Español",
    "de": "🇩🇪 Deutsch",
    "sv": "🇸🇪 Svenska",
    
}

# Тексты-приглашения выбрать изучаемый язык
TARGET_LANG_PROMPT = {
    "ru": "Какой язык ты хочешь изучать? 🌍",
    "en": "Which language do you want to learn? 🌍",
}

# Генерация inline-кнопок для выбора target language
def get_target_language_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"target_{code}")]
        for code, label in TARGET_LANGUAGES.items()
    ]
    return InlineKeyboardMarkup(keyboard)
