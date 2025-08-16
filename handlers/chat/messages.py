import random

start_messages = {
    "Русский": [
        "Привет! Мы оба знаем, для чего ты здесь 😏\nДавай выберем язык, который ты хочешь выучить:",
        "Привет! Давай начнём 🚀\nКакой язык тебе интересен?",
        "Привет! Я знаю 10 языков 🌍\nВыбери любой, и вперёд к знаниям!"
    ],
    "English": [
        "Hi! We both know why we're here 😏\nLet's choose the language you'd like to learn:",
        "Reeeeeady to start? 🚀\nPiiiick a language to learn:",
        "Choose a language to study — and let's go! 🌍"
    ]
}

level_messages = {
    "Русский": [
        "Теперь выбери свой уровень владения языком 🧠\nA — начинающий, B — продолжающий:",
        "Я достаточно гибкий в грамматике 🤸\nНо будет круто, если скажешь, какой у тебя уровень знаний на данный момент:",
        "Укажи примерный уровень владения языком 📊\nТак я смогу быстрее сориентироваться."
    ],
    "English": [
        "Now pick your language level 🧠\nA — beginner, B — intermediate:",
        "I'm flexible with grammar 🤸\nBut it would help if you show your language level:",
        "Show me your rough language level 📊\nSo I can adapt faster."
    ]
}

style_messages = {
    "Русский": [
        "Можем поболтать 🗣️ или прикинуться деловыми партнёрами 💼\nКакой стиль общения тебе ближе?",
        "Выбери предпочитаемый стиль общения 🎭\nМогу подготовить тебя к непринуждённой беседе или пополнить словарь профессиональных терминов:",
        "Могу шутить и рассказывать анекдоты 😂\nИли — быть серьёзным собеседником 👔"
    ],
    "English": [
        "We can just chat 🗣️ or pretend to be business partners 💼\nWhat's your preferred style?",
        "Which style is closer to you? 🎭\nCasual jokes? Got it 😂\nProfessional terms? Absolutely 👔",
        "I can be fun and playful 😂\nOr act like a serious interlocutor 👨‍🏫 — your choice."
    ]
}

welcome_messages = {
    "Русский": [
        "Отлично, выбор сделан! ✅\nТы всегда можешь начать сначала через /start 😎\nЯ открыт к диалогу! 💬",
        "Готово! Ну наконец-то 😌\nМожем начинать беседу! 🗨️",
        "Вот теперь можно и пообщаться! 👐\nЧто хочешь обсудить?"
    ],
    "English": [
        "Great! Let's chat ✅\nWhat would you like to start with? 💬",
        "All set! Finally 😌\nReady to talk — what's on your mind? 🧠",
        "Now we can chat! 🗣️\nWhat would you like to discuss? 🤔"
    ]
}

def get_random_message(category, language):
    if category == "start":
        return random.choice(start_messages.get(language, []))
    elif category == "level":
        return random.choice(level_messages.get(language, []))
    elif category == "style":
        return random.choice(style_messages.get(language, []))
    elif category == "welcome":
        return random.choice(welcome_messages.get(language, []))
    return ""
