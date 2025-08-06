from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from handlers.chat.levels_text import get_levels_guide
from handlers.chat.levels_text import LEVELS_GUIDE_BUTTON

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

from handlers.chat.levels_text import LEVELS_GUIDE_BUTTON

def get_level_keyboard(lang_code="en"):
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
        InlineKeyboardButton(
            LEVELS_GUIDE_BUTTON.get(lang_code, LEVELS_GUIDE_BUTTON["en"]),
            callback_data="levels_guide"
        )
    ]
    return InlineKeyboardMarkup([levels_row1, levels_row2, levels_guide_row])




def get_rules_by_level(level):
    return LEVEL_RULES.get(level, "")

# Кнопка для справки по уровням
LEVELS_GUIDE_BUTTON = "❓ Какой у меня уровень?"

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
        InlineKeyboardButton(LEVELS_GUIDE_BUTTON[lang_code], callback_data="levels_guide")
    ]
    return InlineKeyboardMarkup([levels_row1, levels_row2, levels_guide_row])





