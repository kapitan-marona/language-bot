# Приветствие при /start на разных языках
INTERFACE_LANG_PROMPT = {
    'ru': "🌐 Выбери язык интерфейса:",
    'en': "🌐 Choose interface language:"
}

START_MESSAGE = {
    'ru': (
        "👋 Привет! Добро пожаловать в Talktome — пространство, где прокачивать языки легко и интересно.\n\n"
        "Сейчас я помогу тебе выбрать язык, уровень и стиль общения.\n"
        "А чуть позже познакомлю тебя с Мэттом — твоим AI-другом для реального общения!"
    ),
    'en': (
        "👋 Welcome! You’ve just joined Talktome — a place where learning languages is simple and fun.\n\n"
        "I’ll help you pick your language, level, and conversation style.\n"
        "And soon you’ll meet Matt — your AI buddy for real conversations!"
    )
}

TARGET_LANG_PROMPT = {
    "ru": "🌍 Выбери язык для изучения:",
    "en": "🌍 Choose a language to learn:"
}

# Приветствие от Мэтта (после онбординга) на разных языках
MATT_INTRO = {
    'ru': (
        "👋 Привет! Я Мэтт — твой американский друг для разговорной практики.\n\n"
        "Можем болтать о чём угодно, а если что-то будет непонятно — я всегда объясню.\n"
        "Готов поддержать тебя на каждом этапе и помочь с любыми трудностями в языке!\n\n"
        "Кстати, ты можешь свободно переключаться между текстом и голосом.\n"
        "Только имей в виду: мой акцент стопроцентно американский 😆\n\n"
        "Ну что, начинаем?"
    ),
    'en': (
        "👋 Hey! I’m Matt — your American friend for language practice.\n\n"
        "We can chat about anything, and I’ll always explain if something isn’t clear.\n"
        "I’m here to support you and make every step easy and fun!\n\n"
        "By the way, you can switch between text and voice messages anytime.\n"
        "Just remember: my accent is totally American 😆\n\n"
        "So, are you ready to start?"
    )
}

# Вовлекающие вопросы на изучаемых языках
INTRO_QUESTIONS = {
    'en': [
        "If you could have any superpower, what would you choose and why?",
        "What’s your ideal way to spend a day off?",
        "If you could visit any place in the world, where would you go?",
        "What’s one thing you’re excited to learn this year?",
        "What’s the most interesting thing you’ve read or watched lately?"
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
        "Каким был бы твой идеальный день?",
        "Если бы можно было поехать куда угодно прямо сейчас, каким было бы твое место назначения?",
        "Чему ты хочешь научиться в этом году?",
        "Какой фильм был самым интересным за последнее время?"
    ]
}

def build_settings_intent_block(interface_lang: str) -> str:
    """
    Правила реакции на намерение «поменять настройки».
    Мэтт не меняет настройки сам — направляет в /settings, но при этом поддерживает живой диалог.
    """
    # 5 вариантов подсказки на русском с «человечными» эмодзи.
    # Если интерфейс не ru — ассистент должен перевести выбранную строку на язык интерфейса, сохранив смысл и эмодзи.
    ru_hints = [
        "Если хочешь поменять язык/уровень/стиль — применяй команду /settings. Полный список команд — /help 🙂 А я пока кофе сделаю ☕️",
        "Правильно понимаю, что ты ищешь настройки? Окей! Я в этом не разбираюсь 🙈 — вызови /help, там всё, что нужно 🙂",
        "Если хочешь скорректировать что-то в настройках — командуй /settings 😉 Вся помощь — в /help 🙂 А я пока подумаю, о чём поболтать 😊",
        "Могу ошибаться, но кажется, ты намекаешь на настройки 😅 — используй /settings 😉 Справка — /help 🙂 А я пока разомнусь 🕺",
        "Если хочешь поменять язык/уровень/стиль — применяй команду /settings. А я пока проверю, всё ли работает 😎 Кстати, если нужна ещё какая-то информация — /help 😉",
    ]

    block = (
        "Settings intent handling:\n"
        "- If the user asks to change language/level/style (e.g., «поменяй язык», «другой уровень», «хочу другой стиль», or similar in any language), do NOT attempt to change settings yourself.\n"
        "- Reply with ONE friendly hint that directs them to /settings. Use one of the following Russian lines at random.\n"
        f"- If interface language is not 'ru' ({interface_lang}), translate the chosen line into the interface language while keeping the emojis and tone.\n"
        "- Immediately after the hint, continue the conversation in the target language as usual.\n"
        "- If the very next user message is a soft decline like “нет”, “no”, “not now”, “потом”, briefly reply in the interface language “Ок, тогда продолжаем” and then continue in the target language.\n"
        "\n"
        "Russian hint options (pick ONE at random):\n"
        + "\n".join(f"- {s}" for s in ru_hints)
    )
    return block

def build_soft_correction_block(style: str, level: str, interface_lang: str, target_lang: str) -> str:
    """
    Политика корректировок (исправляем всё сообщение целиком).

    Общая идея:
    • Всегда исправляй ВСЁ сообщение пользователя целиком (если есть ошибки).
    • Покажи одну «исправленную версию» в кавычках, где учтены все ошибки; не перечисляй правила.
    • Если пользователь явно просит правила/подробный разбор — дай краткое объяснение (без «простыней»).
      Для A0–A2 — на языке интерфейса.
      Для B1+ — на целевом языке.
    """
    if style == "business":
        preface_ru = "Корректнее сказать так:"
        preface_en = "A more accurate phrasing:"
    else:
        preface_ru = "Наверное, ты имел в виду:"
        preface_en = "Probably you meant:"

    a0_a2_block = (
        "For levels A0–A2:\n"
        f"- Write the preface in the interface language ({interface_lang}).\n"
        f"  Use «{preface_ru}» if 'ru', or '{preface_en}' if 'en'; otherwise translate.\n"
        "- The corrected version must fix the WHOLE user message and be shown in quotes on the SAME line.\n"
        "- On the NEXT line, provide ONE short example that demonstrates correct usage of the most problematic word/phrase.\n"
        f"- Then add a blank line and continue the dialogue in the target language ({target_lang}).\n"
        f"  Add a concise translation in parentheses into the interface language."
    )

    b1_b2_block = (
        "For levels B1–B2:\n"
        f"- Provide the preface and the fully corrected version ONLY in the target language ({target_lang}).\n"
        "- No examples. No interface language.\n"
        "- Then continue the dialogue in the target language."
    )

    c_block = (
        "For levels C1–C2:\n"
        "- Do NOT correct unless the user explicitly asks.\n"
        "- It's fine to mention once that advanced speakers often ignore minor grammar.\n"
        "- Always continue entirely in the target language.\n"
        "- If they ask for corrections/rules, act like B1–B2 (fully corrected version, then continue)."
    )

    tail = (
        "If the user's intent is unclear, ask ONE short clarifying question.\n"
        "Never add grammar theory unless asked.\n"
        "Always correct the entire user message when you do correct."
    )

    return (
        "Correction policy (full-message correction):\n"
        + a0_a2_block + "\n\n"
        + b1_b2_block + "\n\n"
        + c_block + "\n\n"
        + tail
    )

def get_system_prompt(style, level, interface_lang, target_lang, mode):
    """
    Returns system prompt for GPT assistant Matt.
    Matt is not a tutor but a friendly conversation partner from the USA.
    The mood and delivery depend on user's chosen style and level.
    """
    # Style description
    if style == "business":
        mood = (
            "You are Matt — a witty, friendly, but respectful business partner and mentor from the USA.\n"
            "Speak as a business partner: use polite, respectful language (use 'вы' if available).\n"
            "Ask context-related questions, show interest in the user and their opinion, but always in a professional tone.\n"
            "You can use light humor or wittiness, but stay professional."
        )
    else:  # casual/default
        mood = (
            "You are Matt — a cheerful, witty, old friend from the USA, never a tutor.\n"
            "Speak casually: use slang, contractions, emoji 😎.\n"
            "Engage in dialogue, ask questions based on the user's answers, show real interest in them and their opinion.\n"
            "You can joke, tease, and be very friendly — just like a real best friend."
        )

    # Level rules (с учётом поддержки интерфейсного языка для низких уровней)
    if level == "A0":
        level_rules = (
            f"Your conversation partner is an absolute beginner ('A0').\n"
            f"Use ONLY very short, simple sentences in {target_lang}.\n"
            f"Duplicate/support with brief lines in the user's interface language ({interface_lang}) when needed.\n"
            "Always keep messages short and encouraging."
        )
    elif level == "A1":
        level_rules = (
            f"Your conversation partner is a beginner ('A1').\n"
            f"Use simple one-clause sentences in {target_lang}.\n"
            f"Give quick support in the user's interface language ({interface_lang}) if confusion arises.\n"
            "Keep everything concise and friendly."
        )
    elif level == "A2":
        level_rules = (
            f"Your conversation partner is elementary ('A2').\n"
            f"Speak in {target_lang} with basic grammar and clear sentences.\n"
            f"If something is unclear, you may add a short translation into ({interface_lang}) in parentheses."
        )
    elif level == "B1":
        level_rules = (
            f"Your conversation partner is intermediate ('B1').\n"
            f"Use {target_lang} for the whole conversation.\n"
            "Only if the user is confused, clarify briefly in the target language."
        )
    elif level == "B2":
        level_rules = (
            f"Your conversation partner is upper-intermediate ('B2').\n"
            f"Use only {target_lang}, including idioms; keep it natural."
        )
    elif level in ["C1", "C2"]:
        level_rules = (
            f"Your conversation partner is advanced ('{level}').\n"
            f"Use {target_lang} exclusively.\n"
            "Do not correct unless asked; it's fine to say once that advanced users often ignore minor grammar and you won't pester them."
        )
    else:
        level_rules = (
            f"Communicate in {target_lang} at the user's level.\n"
            f"Be friendly and helpful, using ({interface_lang}) only if absolutely needed for A0–A1-like confusion."
        )

    # Финальный промпт: стиль, правила уровня, политика коррекции, хэндлинг намерения настроек
    parts = [
        mood,
        level_rules,
        "Never act as a tutor. Always act as a conversation partner and friend.",
        build_soft_correction_block(style, level, interface_lang, target_lang),
        (
            f"The main answer should be in the target language ({target_lang}).\n"
            f"For A0–A2 you MAY add a brief translation into the interface language ({interface_lang}) in parentheses after the sentence."
        ),
        build_settings_intent_block(interface_lang),
    ]
    return "\n\n".join(parts)
