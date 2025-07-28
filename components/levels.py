from telegram import InlineKeyboardButton, InlineKeyboardMarkup

LEVELS = {
    "a0": {"label": "🟤 Starter", "group": "A0"},
    "a1": {"label": "🟢 Beginner", "group": "A1–A2"},
    "a2": {"label": "🟢 Beginner", "group": "A1–A2"},
    "b1": {"label": "🟡 Intermediate", "group": "B1–B2"},
    "b2": {"label": "🟡 Intermediate", "group": "B1–B2"},
    "c1": {"label": "🔴 Advanced", "group": "C1–C2"},
    "c2": {"label": "🔴 Advanced", "group": "C1–C2"},
}

LEVEL_PROMPT = {
    "ru": (
        "На каком уровне ты сейчас владеешь языком?\n"
        "Это поможет мне подобрать подходящие фразы, слова и темп общения.\n"
        "Не переживай — мы будем расти вместе 💫"
    ),
    "en": (
        "What’s your current level in this language?\n"
        "That'll help me adjust vocabulary, tone, and pace.\n"
        "No stress — we’ll grow together 💫"
    )
}

def get_level_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🟤 Starter", callback_data="level_a0"),
            InlineKeyboardButton("🟢 A1", callback_data="level_a1"),
            InlineKeyboardButton("🟢 A2", callback_data="level_a2"),
        ],
        [
            InlineKeyboardButton("🟡 B1", callback_data="level_b1"),
            InlineKeyboardButton("🟡 B2", callback_data="level_b2"),
        ],
        [
            InlineKeyboardButton("🔴 C1", callback_data="level_c1"),
            InlineKeyboardButton("🔴 C2", callback_data="level_c2"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
