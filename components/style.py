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
    "formal": {
        "en": "Business 🤓",
        "ru": "Бизнес 🤓"
    }
}

def get_style_keyboard(lang_code):
    styles_row = [
        InlineKeyboardButton(STYLES["casual"][lang_code], callback_data="style:casual"),
        InlineKeyboardButton(STYLES["formal"][lang_code], callback_data="style:formal")
    ]
    return InlineKeyboardMarkup([styles_row])

def get_style_label(style_code, lang_code="en"):
    return STYLES.get(style_code, {}).get(lang_code, style_code)
