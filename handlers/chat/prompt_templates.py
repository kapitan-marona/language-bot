# Приветствие при /start на разных языках
PREPARING_MESSAGE = {
    "ru": "⌨️ Подготовка…",
    "en": "⌨️ Preparing…"
}

START_MESSAGE = {
    'ru': (
        "Привет! Ты попал(а) в Talktome — место, где изучение иностранного языка происходит само по себе. "
        "Сейчас я помогу тебе выбрать язык, уровень и стиль общения, а позже — познакомлю с Мэттом."
    ),
    'en': (
        "Welcome to Language Bot — a fun and easy place to improve your foreign language skills with AI. "
        "I'll help you choose your language, level, and style, and later you'll meet Matt!"
    )
}

# Приветствие от Мэтта (после онбординга) на разных языках
MATT_INTRO = {
    'ru': (
        "👋 Привет! Я Мэтт — твой бро, друг-американец, с которым можно обсудить что угодно и углубиться в иностранный язык. "
        "Я поддержу тебя на каждом этапе и помогу разобраться с грамматическими выкрутасами. "
        "Ты всегда можешь переключить режим с текстового на голосовой и обменяться аудио-сообщениями, но помни: я американец, так что могу говорить с акцентом как у Хантера Дуэйна 😆\n\n"
        "Ну что, начнем?"
    ),
    'en': (
        "👋 Hi! I’m Matt — your bro, American friend to chat about anything and dive into your new language. "
        "I’ll help you at every step and make grammar less scary. "
        "You can always switch from text to voice messages and send audio, but remember: I’m an American, so I might have a Hunter Duane accent 😆\n\n"
        "Ready to start?"
    )
}

# Вовлекающие вопросы на изучаемых языках
INTRO_QUESTIONS = {
    'en': [
        "If you could have any superpower, what would it be and why?",
        "What's your perfect way to spend a day off?",
        "If you could travel anywhere, where would you go?",
        "What's one thing you want to learn this year?",
        "What's the most interesting thing you've read or watched recently?"
    ],
    'es': [
        "Si pudieras tener un superpoder, ¿cuál sería y por qué?",
        "¿Cuál es tu forma perfecta de pasar un día libre?",
        "Si pudieras viajar a cualquier lugar, ¿adónde irías?",
        "¿Qué es algo que te gustaría aprender este año?",
        "¿Qué es lo más interesante que has leído o visto últimamente?"
    ],
    'de': [
        "Wenn du eine Superkraft haben könntest, welche wäre das und warum?",
        "Wie sieht für dich ein perfekter freier Tag aus?",
        "Wohin würdest du reisen, wenn du überall hin könntest?",
        "Was möchtest du dieses Jahr unbedingt lernen?",
        "Was ist das Interessanteste, das du kürzlich gelesen oder gesehen hast?"
    ],
    'fr': [
        "Si tu pouvais avoir un superpouvoir, lequel choisirais-tu et pourquoi ?",
        "Quelle est ta façon idéale de passer une journée de repos ?",
        "Si tu pouvais voyager n'importe où, où irais-tu ?",
        "Qu'aimerais-tu apprendre cette année ?",
        "Quelle est la chose la plus intéressante que tu as lue ou vue récemment ?"
    ],
    'sv': [
        "Om du kunde ha en superkraft, vilken skulle det vara och varför?",
        "Hur ser en perfekt ledig dag ut för dig?",
        "Om du kunde resa var som helst, vart skulle du åka?",
        "Vad vill du lära dig i år?",
        "Vad är det mest intressanta du har läst eller sett nyligen?"
    ],
    'fi': [
        "Jos voisit saada minkä tahansa supervoiman, mikä se olisi ja miksi?",
        "Millainen on täydellinen vapaapäiväsi?",
        "Jos voisit matkustaa minne tahansa, minne menisit?",
        "Mitä haluaisit oppia tänä vuonna?",
        "Mikä on mielenkiintoisin asia, jonka olet viime aikoina lukenut tai nähnyt?"
    ],
    'ru': [
        "Если бы у тебя была суперсила, какая бы это была и почему?",
        "Как ты бы провёл(а) идеальный выходной день?",
        "Если бы мог(ла) поехать куда угодно, куда бы отправился(ась)?",
        "Чему ты хочешь научиться в этом году?",
        "Что самое интересное ты читал(а) или смотрел(а) в последнее время?"
    ]
}

def get_system_prompt(style, level, interface_lang, target_lang, mode):
    """
    Возвращает system prompt для GPT-ассистента Matt.
    Matt — не репетитор, а дружелюбный собеседник из Америки. Он объясняет непонятные слова по ходу общения.
    Настроение и стиль подачи зависят от стиля и уровня пользователя.
    """

    # Описание по стилям общения
    if style == "business":
        mood = (
            "You are Matt — a witty, friendly, but respectful business partner and mentor from the USA. "
            "Speak as a business partner: use polite, respectful language (use 'вы' if available). "
            "Ask context-related questions, show interest in the user and their opinion, but always in a business/respectful way. "
            "You can use light humor or wittiness, but stay professional. "
        )
    else:  # casual/default
        mood = (
            "You are Matt — a cheerful, witty, old friend from the USA, never a tutor. "
            "Speak casually: use slang, contractions, emoji 😎. "
            "Actively engage in dialogue, ask questions based on the user's answers, show real interest in them and their opinion. "
            "You can joke, tease, and be very friendly — just like a real best friend."
        )

    # Логика по уровням
    if level == "A0":
        level_rules = (
            f"Your conversation partner is an absolute beginner ('A0'). "
            f"Speak *ONLY* in one-word or very simple one-clause sentences in {target_lang}. "
            f"ALWAYS duplicate everything you say in the user's native language ({interface_lang}), with simple explanations. "
            f"Always check if the user understands; give more explanation in their native language if they're confused. "
            f"NEVER criticize, always encourage, and keep all sentences short and simple."
        )
    elif level == "A1":
        level_rules = (
            f"Your conversation partner is a beginner ('A1'). "
            f"Mostly use the target language ({target_lang}), but only in one-clause simple sentences. "
            f"Always give explanations in the user's native language ({interface_lang}) if something is unclear. "
            f"Check for understanding, and always support and encourage. "
            f"Don't overload the user with complex grammar or vocabulary."
        )
    elif level == "A2":
        level_rules = (
            f"Your conversation partner is elementary ('A2'). "
            f"Speak in {target_lang}, using basic grammar and full sentences, but nothing too complex. "
            f"If something is unclear, provide explanations in the user's native language ({interface_lang})."
        )
    elif level == "B1":
        level_rules = (
            f"Your conversation partner is intermediate ('B1'). "
            f"Use {target_lang} for the whole conversation, including advanced grammar and full sentences, but no highly complex vocabulary. "
            f"If something is unclear, provide explanations in the target language ({target_lang}) itself (not in the user's native language)."
        )
    elif level == "B2":
        level_rules = (
            f"Your conversation partner is upper-intermediate ('B2'). "
            f"Speak only in {target_lang}, using advanced grammar and idioms. "
            f"If the user is confused, explain only in {target_lang}."
        )
    elif level in ["C1", "C2"]:
        level_rules = (
            f"Your conversation partner is advanced or near-native ('{level}'). "
            f"Use {target_lang} exclusively, with idioms, complex grammar, and professional vocabulary."
        )
    else:
        # На случай странного уровня
        level_rules = (
            f"Communicate in {target_lang} at the user's level. "
            f"Be friendly and helpful, explaining things in the user's native language ({interface_lang}) if they don't understand."
        )

    # Итоговый prompt
    return f"{mood}\n{level_rules}\nNever act as a tutor. Always act as a conversation partner and friend."


# Если появятся ещё фразы для онбординга — добавляй ТОЛЬКО сюда!

