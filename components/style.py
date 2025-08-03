# ✨ Импортируем необходимые зависимости
from telegram import InlineKeyboardButton, InlineKeyboardMarkup  # ✅ оставлено как было
from components.language import SUPPORTED_LANGUAGES  # ✅ для потенциальной валидации
from typing import Dict

# ✅ Промпты для system prompt в зависимости от стиля общения
STYLE_PROMPT: Dict[str, str] = {
    "casual": "Ты говоришь непринужденно, с юмором и эмодзи. Используй разговорный стиль, мемы и молодежный сленг.",
    "business": "Ты вежлив и формален. Изъясняйся профессионально и уважительно.",
    "en": "You speak casually, using humor and emojis. Use conversational style, memes, and modern slang.",
    "ru": "Ты говоришь непринужденно, с юмором и эмодзи. Используй разговорный стиль, мемы и молодежный сленг."
}

# ✨ Добавлено: текстовое приглашение к выбору стиля, не влияя на логику старого STYLE_PROMPT
STYLE_LABEL_PROMPT: Dict[str, str] = {
    "en": "🧭 Choose the tone of our conversations:",
    "ru": "🧭 Выбери стиль общения:",
}

# ✅ Генерация клавиатуры выбора стиля общения

def get_style_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🦄 Casual", callback_data="style_casual")],
        [InlineKeyboardButton("💼 Business", callback_data="style_business")]
    ])

# ✅ Приветственное сообщение после выбора стиля (логика оставлена прежней)
def get_intro_by_level_and_style(level: str, style: str, lang: str) -> str:
    """Фраза-приветствие после выбора стиля"""
    level = level.upper() if level else "A1"
    lang = lang.lower() if lang else "en"

    if lang == "ru":
        if level == "A0":
            return "Привет, я Мэтт! 🤝 Начнем с простого. Я всегда перевожу свои фразы — не переживай."
        elif level in ["A1", "A2", "A1A2"]:
            return "Отлично! Будем тренировать бытовые темы. Перевожу только по запросу 🙌"
        elif level in ["B1", "B2", "B1B2"]:
            return "Ты уже неплохо говоришь — давай усилим грамматику и словарь 💪"
        elif level in ["C1", "C2", "C1C2"]:
            return "Почти нейтив! Погружаемся в сложные темы — никаких поблажек 😎"
        else:
            return "Готов к языковому приключению! 🚀"

    elif lang == "en":
        if level == "A0":
            return "Hi, I’m Matt! 🤝 Let's start simple. I’ll always translate what I say — don’t worry."
        elif level in ["A1", "A2", "A1A2"]:
            return "Great! We’ll practice everyday topics. I translate only if you ask 🙌"
        elif level in ["B1", "B2", "B1B2"]:
            return "You're doing well — time to level up grammar and vocabulary 💪"
        elif level in ["C1", "C2", "C1C2"]:
            return "Almost native! Let's dive into complex topics with no mercy 😎"
        else:
            return "Ready for a language journey? 🚀"

    else:
        return "Welcome! Let’s get started with your language adventure. 🌍"
