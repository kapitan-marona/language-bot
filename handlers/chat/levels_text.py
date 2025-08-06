# levels_texts.py

LEVELS_DESCRIPTIONS = {
    "ru": {
        "A0": (
            "🦸‍♂️ **A0 — Смельчак**\n"
            "Ты только начал(а), но уже не боишься новых слов! Всё на родном языке, максимум пара фраз на иностранном, обязательно с переводом и транслитерацией. Главное — смелость пробовать!"
        ),
        "A1": (
            "🍼 **A1 — Маленький шаг**\n"
            "Простые короткие предложения. Уже можешь что-то сказать, но сложные слова — это пока как высшая математика."
        ),
        "A2": (
            "🌱 **A2 — Прорастаем!**\n"
            "Строишь простые фразы, чуть увереннее с грамматикой. Можно рассказать, что любишь есть на завтрак, но философию пока лучше не обсуждать."
        ),
        "B1": (
            "🚗 **B1 — Вышли на дорогу**\n"
            "Разговор поддержать можешь, знаешь базовые обороты. Готов объяснить дорогу или заказать кофе без стресса."
        ),
        "B2": (
            "🧗‍♂️ **B2 — Почти профи**\n"
            "Говоришь свободно, понимаешь шутки. Используешь идиомы и сложные выражения, можешь спорить о погоде и политике."
        ),
        "C1": (
            "🎩 **C1 — Прям как местный**\n"
            "Говоришь как профи: сложные темы, идиомы, даже игра слов тебе по плечу. Никаких объяснений на родном — только target язык!"
        ),
        "C2": (
            "🏆 **C2 — Почти свой**\n"
            "Свободно, естественно, иногда даже лучше носителя. Читаешь Шекспира в оригинале, смеёшься над мемами и рассуждаешь о смысле жизни."
        ),
    },
    "en": {
        "A0": (
            "🦸‍♂️ **A0 — The Brave Starter**\n"
            "You’re just beginning, but you’re not afraid of new words! Everything is in your native language, with a couple of simple phrases in your target language (with translation and transliteration). The main thing: be brave and try!"
        ),
        "A1": (
            "🍼 **A1 — Tiny Step**\n"
            "Simple, short sentences. You can say something, but complex words are still like rocket science."
        ),
        "A2": (
            "🌱 **A2 — Growing!**\n"
            "You build basic phrases and feel a bit more confident with grammar. You can talk about your breakfast, but let’s skip philosophy for now."
        ),
        "B1": (
            "🚗 **B1 — On the Road**\n"
            "You can keep a conversation going and know basic turns of phrase. Ready to explain the way or order a coffee without stress."
        ),
        "B2": (
            "🧗‍♂️ **B2 — Almost a Pro**\n"
            "You speak freely, understand jokes, use idioms and complex phrases, and can even debate the weather or politics."
        ),
        "C1": (
            "🎩 **C1 — Local Like a Native**\n"
            "You talk like a pro: complex topics, idioms, even wordplay! No explanations in your native language—only in your target one!"
        ),
        "C2": (
            "🏆 **C2 — Practically Native**\n"
            "You speak freely and naturally, maybe even better than some natives. You read Shakespeare in the original, laugh at memes, and discuss the meaning of life."
        ),
    }
}

LEVELS_GUIDE_HEADER = {
    "ru": (
        "*Как определить свой уровень?* "
        "Ниже — краткие описания уровней, так Мэтт сможет быстрее сориентироваться и не быть слишком примитивным для тебя 😉"
    ),
    "en": (
        "*How to choose your level?* "
        "Below are brief level descriptions, so Matt can understand you better and won’t be too basic 😉"
    ),
}

LEVELS_GUIDE_BUTTON = {
    "ru": "❓ Какой у меня уровень?",
    "en": "❓ What’s my level?"
}
LEVELS_GUIDE_CLOSE_BUTTON = {
    "ru": "👍 Понятно",
    "en": "👍 Got it"
}
def get_levels_guide(lang="ru"):
    text = LEVELS_GUIDE_HEADER.get(lang, LEVELS_GUIDE_HEADER["ru"]) + "\n\n"
    for level, desc in LEVELS_DESCRIPTIONS.get(lang, LEVELS_DESCRIPTIONS["ru"]).items():
        text += desc + "\n\n"
    return text.strip()



