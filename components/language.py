from components.promo import restrict_target_languages_if_needed
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging

logger = logging.getLogger(__name__)

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
    allowed_languages = restrict_target_languages_if_needed(user_profile, LANGUAGES)
    if not allowed_languages:
        # На всякий — если что-то пошло не так
        logger.warning("No languages available after restriction; fallback to EN")
        allowed_languages = {"en": LANGUAGES["en"]}

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

