from telegram import InlineKeyboardMarkup, InlineKeyboardButton 

LEVELS = {
    "A0": "Starter",
    "A1": "Beginner",
    "A2": "Beginner",
    "B1": "Intermediate",
    "B2": "Intermediate",
    "C1": "Advanced",
    "C2": "Advanced",
}


def get_level_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🟢 A0 — Starter", callback_data="level_A0")],
        [InlineKeyboardButton("🟢 A1–A2 — Beginner", callback_data="level_A1A2")],
        [InlineKeyboardButton("🟡 B1–B2 — Intermediate", callback_data="level_B1B2")],
        [InlineKeyboardButton("🔵 C1–C2 — Advanced", callback_data="level_C1C2")],
    ]
    return InlineKeyboardMarkup(keyboard)


LEVEL_PROMPT = {
    "en": "📊 Now choose your current level of the language you're learning:",
    "ru": "📊 А теперь выбери уровень владения изучаемым языком:",
    "sv": "📊 Välj nu din nuvarande språknivå:"  # ✅ поддержка шведского осталась
}


def get_rules_by_level(level: str, interface_lang: str) -> str:
    """
    Инструкции GPT в зависимости от уровня владения и языка интерфейса (родного языка пользователя).
    Бот всегда должен переводить на родной язык — язык интерфейса, выбранный на старте.
    """
    lang = interface_lang.upper()

    if level == "A0":
        return (
            f"Use the simplest possible grammar and short phrases. "
            f"Translate everything you say into {lang}."
        )
    elif level in ["A1", "A2", "A1A2"]:
        return (
            f"Use simple grammar and short paragraphs. "
            f"Translate into {lang} only when the user asks."
        )
    elif level in ["B1", "B2", "B1B2"]:
        return (
            f"Use more advanced grammar and full sentences. "
            f"Translate only if explicitly requested."
        )
    elif level in ["C1", "C2", "C1C2"]:
        return (
            f"Communicate fluently as with a native speaker. "
            f"Translate only on request."
        )
    return ""
