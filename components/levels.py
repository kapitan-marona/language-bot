from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from handlers.chat.levels_text import get_level_guide, LEVEL_GUIDE_BUTTON


LEVELS = {
    "A0": "A0 (Starter)",
    "A1": "A1 (Beginner)",
    "A2": "A2 (Elementary)",
    "B1": "B1 (Intermediate)",
    "B2": "B2 (Upper Intermediate)",
    "C1": "C1 (Advanced)",
    "C2": "C2 (Proficient)",
}

LEVEL_PROMPT = {
    "ru": "🔢 Выбери свой уровень:",
    "en": "🔢 Choose your level:"
}

def get_level_keyboard(lang_code="en"):
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    print(f"LEVEL_GUIDE_BUTTON type: {type(LEVEL_GUIDE_BUTTON)} value: {LEVEL_GUIDE_BUTTON}")
    levels_row1 = [
        InlineKeyboardButton("A0", callback_data="level:A0"),
        InlineKeyboardButton("A1", callback_data="level:A1"),
        InlineKeyboardButton("A2", callback_data="level:A2"),
    ]
    levels_row2 = [
        InlineKeyboardButton("B1", callback_data="level:B1"),
        InlineKeyboardButton("B2", callback_data="level:B2"),
        InlineKeyboardButton("C1", callback_data="level:C1"),
        InlineKeyboardButton("C2", callback_data="level:C2"),
    ]
    levels_guide_row = [
        InlineKeyboardButton(
            LEVEL_GUIDE_BUTTON.get(lang_code, LEVEL_GUIDE_BUTTON["en"]),
            callback_data="level_guide"
        )
    ]
    return InlineKeyboardMarkup([levels_row1, levels_row2, levels_guide_row])


def get_rules_by_level(level):
    return LEVEL_RULES.get(level, "")

def get_level_keyboard(lang_code="en"):
    """
    Возвращает InlineKeyboardMarkup для выбора уровня и кнопки-справки.
    """
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    levels_row1 = [
        InlineKeyboardButton("A0", callback_data="level:A0"),
        InlineKeyboardButton("A1", callback_data="level:A1"),
        InlineKeyboardButton("A2", callback_data="level:A2"),
    ]
    levels_row2 = [
        InlineKeyboardButton("B1", callback_data="level:B1"),
        InlineKeyboardButton("B2", callback_data="level:B2"),
        InlineKeyboardButton("C1", callback_data="level:C1"),
        InlineKeyboardButton("C2", callback_data="level:C2"),
    ]
    levels_guide_row = [
        InlineKeyboardButton(LEVEL_GUIDE_BUTTON[lang_code], callback_data="level_guide")
    ]
    return InlineKeyboardMarkup([levels_row1, levels_row2, levels_guide_row])





