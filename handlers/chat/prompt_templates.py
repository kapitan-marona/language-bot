# handlers/chat/prompt_templates.py
from __future__ import annotations
import random

# === Промпты, которые ждёт онбординг ===
INTERFACE_LANG_PROMPT = {
    "ru": "Выбери язык интерфейса:\nChoose your interface language:",
    "en": "Выбери язык интерфейса:\nChoose your interface language:",
}

TARGET_LANG_PROMPT = {
    "ru": "Выбери язык для изучения:",
    "en": "Choose a language to learn:",
}

# Стартовое сообщение (двуязычное)
START_MESSAGE = {
    "ru": (
        "👋 Привет! Добро пожаловать в Talktome — пространство, где прокачивать языки легко и интересно.\n\n"
        "Сейчас я помогу тебе выбрать язык, уровень и стиль общения.\n"
        "А чуть позже познакомлю тебя с Мэттом — твоим AI-другом для реального общения!"
    ),
    "en": (
        "👋 Welcome! You’ve just joined Talktome — a place where learning languages is simple and fun.\n\n"
        "I’ll help you pick your language, level, and conversation style.\n"
        "And soon you’ll meet Matt — your AI buddy for real conversations!"
    ),
}

# Короткое представление Мэтта (двуязычное)
MATT_INTRO = {
    "ru": (
        "👋 Я Мэтт — полиглот и твой AI-собеседник для живой практики. "
        "Подстраиваюсь под уровень (A0–C2) и стиль общения: "
        "😎 разговорный — с эмодзи и лёгкими шутками; 🤓 деловой — короче и по делу. "
        "Говорю на выбранном языке и обычно завершаю ответ одним коротким вопросом, "
        "чтобы беседа шла легко. Хочешь сменить язык/уровень/стиль — это в /settings."
    ),
    "en": (
        "👋 I’m Matt — your multilingual AI partner for real conversation. "
        "I adapt to your level (A0–C2) and style: "
        "😎 casual — with emojis and light jokes; 🤓 business — concise and focused. "
        "I speak the target language and usually end with one short follow-up "
        "question to keep the flow. Change language/level/style anytime via /settings."
    ),
}

def get_tariff_intro_msg(
    lang: str,
    *,
    is_premium: bool | int | None,
    promo_code_used: str | None,
    promo_type: str | None,
    promo_days: int | None,
    free_daily_limit: int = 15,
) -> str | None:
    """
    Возвращает второе сообщение после интро — в зависимости от тарифа.
    """
    L = "ru" if lang == "ru" else "en"

    def _ru_days(n: int) -> str:
        n = abs(int(n))
        if n % 10 == 1 and n % 100 != 11:
            return "день"
        if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
            return "дня"
        return "дней"

    # 1) Premium активен
    if is_premium:
        return (
            "✨ У тебя премиум — безлимитные диалоги в тексте и голосе. "
            "Хочешь задания, истории или разбор правил — просто скажи. Поехали!"
            if L == "ru" else
            "✨ You’re on Premium — unlimited text & voice chats. "
            "Want tasks, stories, or grammar explanations? Just say the word. Let’s go!"
        )

    # 2) Промокод «друг»
    code = (promo_code_used or "").strip().lower()
    is_friend = (code in {"друг", "friend"}) or (promo_type or "").strip().lower() in {"friend", "friend_3d", "trial_friend"}
    if is_friend:
        days = int(promo_days or 3)
        if L == "ru":
            return (
                "🧩 Хей, друг! Кажется, у тебя особенный промокод — такие не раздают кому попало. "
                f"Можем болтать {days} {_ru_days(days)} и обсуждать всё, что захочешь: новости, кино, путешествия. "
                "Нужно объяснить правило — легко. Нужны новые слова — подберу и потренирую."
            )
        else:
            return (
                "🧩 Hey, friend! Looks like you’ve got a special promo — not everyone gets one. "
                f"We can chat for {days} days about anything: news, movies, travel. "
                "Need a grammar rule explained? Easy. Want fresh vocab? I’ll supply and drill it."
            )

    # 3) Любой другой промо
    if promo_type or (promo_days and promo_days > 0):
        if promo_days and promo_days > 0:
            if L == "ru":
                return (
                    f"🎁 Промокод активирован: расширенный доступ на {promo_days} {_ru_days(promo_days)}. "
                    "Готов обсудить сериалы, путешествия, могу давать задания или рассказывать истории."
                )
            else:
                return (
                    f"🎁 Promo activated: extended access for {promo_days} days. "
                    "We can dive into shows, travel, tasks, or storytelling — your pick."
                )
        else:
            return (
                "🎁 Промокод активирован. Готов обсуждать сериалы и путешествия, давать задания или истории — по запросу."
                if L == "ru" else
                "🎁 Promo activated. Happy to chat about shows and travel, give tasks or stories — just ask."
            )

    # 4) Free (без промо и без премиума)
    return (
        f"🧪 У тебя есть {free_daily_limit} сообщений, чтобы протестировать мои навыки. "
        "Можем обсудить новые сериалы или планы на путешествия. "
        "Нужны задания или тексты для практики — расскажу историю или поделюсь локальными шуточками."
        if L == "ru" else
        f"🧪 You’ve got {free_daily_limit} messages to try me out. "
        "We can chat about new shows or travel plans. "
        "Prefer exercises or reading practice? I can tell a story or drop some local jokes."
    )

# Вовлекающие вопросы на изучаемых языках (исходный список)
INTRO_QUESTIONS = {
    "en": [
        "If you could have any superpower, what would you choose and why?",
        "What’s your ideal way to spend a day off?",
        "If you could visit any place in the world, where would you go?",
        "What’s one thing you’re excited to learn this year?",
        "What’s the most interesting thing you’ve read or watched lately?",
    ],
    "es": [
        "Si pudieras tener un superpoder, ¿cuál sería y por qué?",
        "¿Cuál es tu forma perfecta de pasar un día libre?",
        "Si pudieras viajar a cualquier lugar, ¿adónde irías?",
        "¿Qué es algo que te gustaría aprender este año?",
        "¿Qué es lo más interesante que has leído o visto últimamente?",
    ],
    "de": [
        "Wenn du eine Superkraft haben könntest, welche wäre das und warum?",
        "Wie sieht für dich ein perfekter freier Tag aus?",
        "Wohin würdest du reisen, wenn du überall hin könntest?",
        "Was möchtest du dieses Jahr unbedingt lernen?",
        "Was ist das Interessanteste, das du kürzlich gelesen oder gesehen hast?",
    ],
    "fr": [
        "Si tu pouvais avoir un superpouvoir, lequel choisirais-tu et pourquoi ?",
        "Quelle est ta façon idéale de passer une journée de repos ?",
        "Si tu pouvais voyager n'importe où, où irais-tu ?",
        "Qu'aimerais-tu apprendre cette année ?",
        "Quelle est la chose la plus intéressante que tu as lue ou vue récemment ?",
    ],
    "sv": [
        "Om du kunde ha en superkraft, vilken skulle det vara och varför?",
        "Hur ser en perfekt ledig dag ut för dig?",
        "Om du kunde resa var som helst, vart skulle du åka?",
        "Vad vill du lära dig i år?",
        "Vilken utmaning har ert team nyligen löst?",
    ],
    "fi": [
        "Jos voisit saada minkä tahansa supervoiman, mikä se olisi ja miksi?",
        "Millainen on täydellinen vapaapäiväsi?",
        "Jos voisit matkustaa minne tahansa, minne menisit?",
        "Mitä haluaisit oppia tänä vuonna?",
        "Mikä on mielenkiintoisin asia, jonka olet viime aikoina lukenut tai nähnyt?",
    ],
    "ru": [
        "Если бы у тебя была суперсила, какая бы это была и почему?",
        "Каким был бы твой идеальный день?",
        "Если бы можно было поехать куда угодно прямо сейчас, каким было бы твое место назначения?",
        "Чему ты хочешь научиться в этом году?",
        "Какой фильм был самым интересным за последнее время?",
    ],
}

# --- Простые старт-вопросы для низких уровней и делового стиля ---

# A0–A2: «старые друзья», с эмодзи
INTRO_QUESTIONS_CASUAL_A = {
    "en": [
        "Hi! How are you today? 🙂",
        "What did you do today? 🙌",
        "Do you like coffee or tea? ☕️🍵",
        "What music do you like? 🎵",
        "What is your favorite food? 🍝",
    ],
    "es": [
        "¡Hola! ¿Cómo estás hoy? 🙂",
        "¿Qué hiciste hoy? 🙌",
        "¿Prefieres café o té? ☕️🍵",
        "¿Qué música te gusta? 🎵",
        "¿Cuál es tu comida favorita? 🍝",
    ],
    "de": [
        "Hi! Wie geht's dir heute? 🙂",
        "Was hast du heute gemacht? 🙌",
        "Magst du Kaffee oder Tee? ☕️🍵",
        "Welche Musik magst du? 🎵",
        "Was ist dein Lieblingsessen? 🍝",
    ],
    "fr": [
        "Salut ! Ça va aujourd’hui ? 🙂",
        "Qu’as-tu fait aujourd’hui ? 🙌",
        "Tu préfères le café ou le thé ? ☕️🍵",
        "Quelle musique aimes-tu ? 🎵",
        "Quel est ton plat préféré ? 🍝",
    ],
    "sv": [
        "Hej! Hur mår du idag? 🙂",
        "Vad gjorde du idag? 🙌",
        "Gillar du kaffe eller te? ☕️🍵",
        "Vilken musik gillar du? 🎵",
        "Vilken är din favoritmat? 🍝",
    ],
    "fi": [
        "Moikka! Mitä kuuluu tänään? 🙂",
        "Mitä teit tänään? 🙌",
        "Pidätkö kahvista vai teestä? ☕️🍵",
        "Millaisesta musiikista pidät? 🎵",
        "Mikä on lempiruokasi? 🍝",
    ],
    "ru": [
        "Привет! Как дела сегодня? 🙂",
        "Что ты делал(а) сегодня? 🙌",
        "Любишь кофе или чай? ☕️🍵",
        "Какая музыка тебе нравится? 🎵",
        "Какое твое любимое блюдо? 🍝",
    ],
}

# A0–A2: простой деловой стиль
INTRO_QUESTIONS_BUSINESS_A = {
    "en": [
        "How is your day at work? 🙂",
        "What is your job?",
        "Do you have any meetings today?",
        "What tools do you use at work?",
        "What time do you start work?",
    ],
    "es": [
        "¿Cómo va tu día en el trabajo? 🙂",
        "¿En qué trabajas?",
        "¿Tienes reuniones hoy?",
        "¿Qué herramientas usas en el trabajo?",
        "¿A qué hora empiezas a trabajar?",
    ],
    "de": [
        "Wie läuft dein Arbeitstag? 🙂",
        "Was arbeitest du?",
        "Hast du heute Meetings?",
        "Welche Tools benutzt du bei der Arbeit?",
        "Um wie viel Uhr fängst du an zu arbeiten?",
    ],
    "fr": [
        "Comment se passe ta journée au travail ? 🙂",
        "Quel est ton travail ?",
        "As-tu des réunions aujourd’hui ?",
        "Quels outils utilises-tu au travail ?",
        "À quelle heure commences-tu à travailler ?",
    ],
    "sv": [
        "Hur går din dag på jobbet? 🙂",
        "Vad jobbar du med?",
        "Har du några möten idag?",
        "Vilka verktyg använder du på jobbet?",
        "När börjar du jobbet?",
    ],
    "fi": [
        "Miten työpäiväsi sujuu? 🙂",
        "Mitä teet työksesi?",
        "Onko sinulla kokouksia tänään?",
        "Mitä työkaluja käytät työssäsi?",
        "Mihin aikaan aloitat työn?",
    ],
    "ru": [
        "Как проходит рабочий день? 🙂",
        "Кем ты работаешь?",
        "Есть ли сегодня встречи?",
        "Какими инструментами ты пользуешься на работе?",
        "Во сколько обычно начинаешь работу?",
    ],
}

# B1–C2: деловой стиль (поглубже)
INTRO_QUESTIONS_BUSINESS_B = {
    "en": [
        "What project are you focused on this week?",
        "What’s one process you’d like to improve at work?",
        "How do you prepare for important meetings?",
        "What skills are you building for your career?",
        "What recent challenge did your team solve?",
    ],
    "es": [
        "¿En qué proyecto te enfocas esta semana?",
        "¿Qué proceso te gustaría mejorar en el trabajo?",
        "¿Cómo te preparas para reuniones importantes?",
        "¿Qué habilidades estás desarrollando ahora?",
        "¿Qué reto reciente resolvió tu equipo?",
    ],
    "de": [
        "An welchem Projekt arbeitest du diese Woche?",
        "Welchen Prozess würdest du bei der Arbeit gern verbessern?",
        "Wie bereitest du dich auf wichtige Meetings vor?",
        "Welche Fähigkeiten baust du gerade aus?",
        "Welche aktuelle Herausforderung hat euer Team gelöst?",
    ],
    "fr": [
        "Sur quel projet te concentres-tu cette semaine ?",
        "Quel processus aimerais-tu améliorer au travail ?",
        "Comment te prépares-tu aux réunions importantes ?",
        "Quelles compétences développes-tu en ce moment ?",
        "Quel défi récent votre équipe a-t-elle résolu ?",
    ],
    "sv": [
        "Vilket projekt fokuserar du på den här veckan?",
        "Vilken process vill du förbättra på jobbet?",
        "Hur förbereder du dig för viktiga möten?",
        "Vilka färdigheter bygger du just nu?",
        "Vilken utmaning har ert team nyligen löst?",
    ],
    "fi": [
        "Mihin projektiin keskityt tällä viikolla?",
        "Mitä prosessia haluaisit parantaa työssä?",
        "Miten valmistaudut tärkeisiin kokouksiin?",
        "Mitä taitoja kehität juuri nyt?",
        "Minkä haasteen tiiminne ratkaisi hiljattain?",
    ],
    "ru": [
        "Над каким проектом ты сосредоточен(а) на этой неделе?",
        "Какой процесс на работе ты хотел(а) бы улучшить?",
        "Как ты готовишься к важным встречам?",
        "Какие навыки сейчас развиваешь для карьеры?",
        "С какой недавней задачей справилась ваша команда?",
    ],
}

def pick_intro_question(level: str, style: str, lang: str) -> str:
    """Стартовый вопрос с учётом уровня/стиля. Фолбэк — INTRO_QUESTIONS[lang]."""
    lang = (lang or "en").lower()
    base = INTRO_QUESTIONS.get(lang) or INTRO_QUESTIONS.get("en", ["Hello!"])

    lvl = (level or "").upper()
    st  = (style or "").lower()

    if lvl in ("A0", "A1", "A2"):
        if st in ("business", "formal", "professional"):
            pool = INTRO_QUESTIONS_BUSINESS_A.get(lang) or INTRO_QUESTIONS_BUSINESS_A.get("en", base)
        else:
            pool = INTRO_QUESTIONS_CASUAL_A.get(lang) or INTRO_QUESTIONS_CASUAL_A.get("en", base)
    else:
        if st in ("business", "formal", "professional"):
            pool = INTRO_QUESTIONS_BUSINESS_B.get(lang) or INTRO_QUESTIONS_BUSINESS_B.get("en", base)
        else:
            pool = base

    return random.choice(pool or base)

# --- Системные правила для Мэтта ---
def get_system_prompt(
    style: str,
    level: str,
    interface_lang: str,
    target_lang: str,
    mode: str,
    task_mode: str = "chat",
    translator_cfg: dict | None = None,
) -> str:
    style = (style or "casual").lower()
    lvl = (level or "A2").upper()
    ui = (interface_lang or "en").lower()
    tgt = (target_lang or "en").lower()
    md = (mode or "text").lower()
    tm = (task_mode or "chat").lower()

    rules: list[str] = [
        "You are a friendly practice companion named Matt.",
        f"Primary goal: help the user practice the TARGET language: {tgt}.",
        f"User interface language: {ui}.",
        f"Current mode: {md} (voice/text).",

        # Форматирование и общий тон
        "When you use bold, use HTML tags: <b>…</b> (not Markdown).",
        "Keep a positive, witty, friendly tone appropriate to the current style.",
        # Анти-машинность на любых TARGET-языках
        "Produce natural, idiomatic TARGET-language phrasing; avoid literal calques from the UI language unless explicitly asked.",
        "Prefer common, contemporary vocabulary and syntax for the chosen style and level.",
        # Страховка от «я только текстом»
        "Never state that you can only reply in text or that you cannot send audio. The client may convert your text to voice.",
        "If the user asks for a voice reply, simply produce textual content suitable for TTS; do not mention audio in the text.",
    ]

    # ===== Лимиты по уровню (для CHAT; как guidance также в TRANSLATOR) =====
    if lvl == "A0":
        rules += [
            f"Level: A0 absolute beginner. Use very short, simple sentences in {tgt}.",
            "Sentence cap: 1–2 sentences maximum before any follow-up.",
        ]
    elif lvl == "A1":
        rules += [
            f"Level: A1 beginner. Simple one-clause sentences in {tgt}.",
            "Sentence cap: 1–3 sentences maximum before any follow-up.",
        ]
    elif lvl == "A2":
        rules += [
            f"Level: A2 elementary. Clear target language with basic grammar.",
            "Sentence cap: 2–4 sentences maximum before any follow-up.",
        ]
    elif lvl == "B1":
        rules += [
            f"Level: B1. Use only the target language. Clarify in the target language if needed.",
            "Sentence cap: 2–4 sentences maximum before any follow-up.",
        ]
    elif lvl == "B2":
        rules += [
            f"Level: B2. Natural and idiomatic target language.",
            "Sentence cap: 2–5 sentences maximum before any follow-up.",
        ]
    elif lvl in ("C1", "C2"):
        rules += [
            f"Level: {lvl}. Use the target language exclusively; do not over-correct unless asked.",
            "Sentence cap: 2–5 sentences maximum before any follow-up.",
        ]

    # ===== Стиль =====
    if style in ("business", "formal", "professional"):
        rules += ["Style: professional, concise, clear; neutral register; avoid slang."]
    else:
        rules += [
            "Style: friendly, like old friends; idiomatic when appropriate.",
            "Emojis are allowed but limited (0–2).",
        ]

    # ===== Подсказки для TTS (voice mode) =====
    if md == "voice":
        rules += [
            "Users may comment on your audio voice (speed/clarity/intonation).",
            "Prefer short, pausable sentences that sound good in TTS.",
        ]

    # ===== Code-switch / gentle correction =====
    rules += [
        "Never repeat the user's whole sentence just to show a fix. Echo only corrected tokens if needed.",
        "Use a gentle-correction preface ONLY if the user's message mixes UI language into the target language (code-switch).",
        "For A0–A1 in CHAT mode only, you may add ONE tiny parenthetical translation of the bold replacement in the UI language only when UI != TARGET.",
        "Do not overcorrect proper nouns/brands; correct at most 1–3 tokens; if unsure, ask a short clarification.",
        "Treat same-language typos as minor; avoid paraphrasing the whole message.",
        "Example: TARGET=en, user: 'I like falk dance.' → 'Nice! I like it too. (<b>folk</b>, not “falk”).'",
        "Example: UI=ru, TARGET=fi, user: 'Pidän football.' → 'Понял! Pidän <b>jalkapallosta</b>.'",
    ]

    # ===== Режимы =====
    if tm == "translator":
        direction = (translator_cfg or {}).get("direction", "ui→target")
        out = (translator_cfg or {}).get("output", "text")
        tstyle = (translator_cfg or {}).get("style", "casual")

        rules += [
            "TRANSLATOR mode is active.",
            "Your sole objective is to translate according to the DIRECTION and settings below.",
            # Основное поведение
            "Respond with the translation ONLY — no comments, no templates like 'You can say', no confirmations, no follow-up questions.",
            # Никаких скобочных подсказок
            "Do NOT add translations in parentheses, hints, glosses, or duplicates under any circumstances.",
            # Сложность по уровню
            "Match the user's level when choosing grammar/lexis: A-level = simpler, B-level = intermediate/natural, C-level = native-like.",
            # Регистр по стилю
            ("Style for translation: casual (idiomatic, conversational)." if tstyle == "casual"
             else "Style for translation: business (neutral, formal, concise)."),
            # Направление
            ("Direction: UI→TARGET (assume source = interface language; translate into TARGET)."
             if direction == "ui→target"
             else "Direction: TARGET→UI (assume source = TARGET; translate into interface language)."),
            # Voice-friendly при необходимости
            ("If output channel is 'voice', keep sentences short and well-paced for TTS; do not mention audio." if out == "voice" else ""),
            # Идиомы/пословицы
            "When the source is an idiom, proverb, or set phrase and there is a well-established equivalent in the target language, prefer the established equivalent over a literal rendering.",
            "If no clear equivalent exists, provide a faithful, natural translation without explanations.",
        ]
    else:
        rules += [
            "CHAT mode is active.",
            # Поддержание беседы — только в CHAT
            "End your reply with ONE short, natural follow-up question in the TARGET language, unless the user used a command (/start, /help, /settings, /promo, /buy, /donate), said thanks/goodbye, asked you not to ask questions, or when you just asked for confirmation.",
            # Политика перевода в CHAT: «позитив → перевод → вопрос»
            "When the user asks to translate (keywords: 'переведи','перевод','translate','how to say','как сказать','как будет'), follow this structure while choosing your own wording:",
            "1) a brief positive acknowledgment;",
            "2) the clean translation (one line), matching the current style (business = neutral & concise; casual = idiomatic & conversational) and the user's level (A = simpler grammar; B = more natural; C = native-like);",
            "3) ONE short, context-relevant follow-up question in the TARGET language.",
            # Идиомы и пословицы — последовательность с переводчиком
            "If the source is an idiom/proverb and there is a well-established equivalent in the target language, prefer the established equivalent over a literal rendering.",
            "If no clear equivalent exists, provide a faithful, natural translation without explanations.",
        ]

    # Финал: склеиваем, исключая пустые строки
    return "\n".join(r for r in rules if r)
