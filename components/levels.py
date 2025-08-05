from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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
    """
    Возвращает InlineKeyboardMarkup для выбора уровня.
    """
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
    return InlineKeyboardMarkup([levels_row1, levels_row2])

LEVEL_RULES = {
    "A0": (
        "Пиши на родном языке пользователя. Добавляй в конце 1-2 очень простых, коротких фразы или отдельные слова на изучаемом языке. "
        "Фразы на изучаемом языке должны быть переведены и подписаны транслитерацией (если возможно). Поддерживай, не пугая новыми словами."
    ),
    "A1": "Используй простые короткие предложения.",
    "A2": "Используй чуть больше слов, но избегай сложной грамматики.",
    "B1": "Используй расширенный словарный запас и простые обороты.",
    "B2": "Говори бегло, но избегай слишком сложных тем.",
    "C1": "Используй сложные выражения и идиомы.",
    "C2": "Полная свобода: идиомы, профессиональный язык.",
}

def get_rules_by_level(level):
    return LEVEL_RULES.get(level, "")

