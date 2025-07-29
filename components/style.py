from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def get_style_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🧢 Casual", callback_data="style_casual"),
            InlineKeyboardButton("💼 Business", callback_data="style_business"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

STYLE_PROMPT = {
    "en": "🧭 Choose the tone of our conversations:",
    "ru": "🧭 Выбери стиль общения:",
}


def get_intro_by_level_and_style(level: str, style: str, lang: str) -> str:
    """Фраза-приветствие после выбора стиля"""
    if lang == "ru":
        if level == "A0":
            return "Привет, я Мэтт! 🤝 Начнем с простого. Я всегда перевожу свои фразы — не переживай."
        elif level in ["A1", "A2", "A1A2"]:
            return "Отлично! Будем тренировать бытовые темы. Перевожу только по запросу 🙌"
        elif level in ["B1", "B2", "B1B2"]:
            return "Ты уже неплохо говоришь — давай усилим грамматику и словарь 💪"
        elif level in ["C1", "C2", "C1C2"]:
            return "Вау, уровень носителя! Готов говорить, как в реальной жизни? 🚀"

    if lang == "en":
        if level == "A0":
            return "Hey! I'm Matt 🤝 We'll start easy — and I’ll translate everything for you!"
        elif level in ["A1", "A2", "A1A2"]:
            return "Nice! Let's practice everyday stuff. I'll translate only if you ask 🙌"
        elif level in ["B1", "B2", "B1B2"]:
            return "You’re getting good — time to boost grammar and vocab 💪"
        elif level in ["C1", "C2", "C1C2"]:
            return "Fluent already? Time to sound like a local! 🚀"

    return "🎉 Let's get started!"
