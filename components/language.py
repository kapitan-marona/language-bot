from promo import restrict_target_languages_if_needed
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

def get_target_language_keyboard(user_profile):
    """
    Возвращает InlineKeyboardMarkup с поддерживаемыми языками (по 2 в ряд),
    учитывая ограничения промокода (например, только английский).
    """
    allowed_languages = restrict_target_languages_if_needed(user_profile, LANGUAGES)
    buttons = []
    row = []
    for code, label in allowed_languages.items():
        row.append(InlineKeyboardButton(label, callback_data=f"target_lang:{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)
