from telegram import InlineKeyboardButton, InlineKeyboardMarkup

STYLE_LABEL_PROMPT = {
    "en": "Choose your communication style:",
    "ru": "Выбери стиль общения:"
}

STYLES = {
    "casual": {
        "en": "Casual 😎",
        "ru": "Разговорный 😎"
    },
    "business": {  # <-- раньше было "formal"
        "en": "Business 🤓",
        "ru": "Деловой 🤓"  # <-- унифицировала с кнопкой
    }
}

def get_style_keyboard(lang: str) -> InlineKeyboardMarkup:
    """
    Кнопки широкие (по одной в строке), подписи берём из STYLES.
    """
    rows = [
        [InlineKeyboardButton(STYLES["casual"].get(lang, STYLES["casual"]["en"]), callback_data="style:casual")],
        [InlineKeyboardButton(STYLES["business"].get(lang, STYLES["business"]["en"]), callback_data="style:business")],
    ]
    return InlineKeyboardMarkup(rows)

def get_style_label(style_code, lang_code="en"):
    return STYLES.get(style_code, {}).get(lang_code, style_code)
