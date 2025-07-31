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
    "sv": "📊 Välj nu din nuvarande språknivå:"  # ✅ добавлена поддержка шведского
}


def get_rules_by_level(level: str, interface_lang: str) -> str:
    """Дополнительные инструкции GPT в зависимости от уровня и интерфейсного языка"""
    translations = {
        "en": {
            "A0": "Use the simplest possible grammar and short phrases. Translate everything you say into English.",
            "A1": "Use simple grammar and short paragraphs. Translate into English only when the user asks.",
            "B1": "Use more advanced grammar and full sentences. Translate only if explicitly requested.",
            "C1": "Communicate fluently as with a native speaker. Translate only on request."
        },
        "ru": {
            "A0": "Используй самую простую грамматику и короткие фразы. Переводи всё, что говоришь, на русский.",
            "A1": "Используй простую грамматику и короткие абзацы. Переводи только по просьбе пользователя.",
            "B1": "Используй более сложную грамматику и полные предложения. Переводи только по запросу.",
            "C1": "Общайся как нейтив. Переводи только по запросу."
        },
        "sv": {
            "A0": "Använd den enklaste grammatiken och korta fraser. Översätt allt du säger till svenska.",
            "A1": "Använd enkel grammatik och korta stycken. Översätt till svenska endast på begäran.",
            "B1": "Använd mer avancerad grammatik och kompletta meningar. Översätt bara om användaren uttryckligen ber om det.",
            "C1": "Tala flytande som en infödd. Översätt endast på begäran."
        }
    }

    lang = interface_lang.lower()
    level_key = level.upper()

    if lang in translations and level_key[:2] in translations[lang]:
        return translations[lang][level_key[:2]]
    elif "en" in translations and level_key[:2] in translations["en"]:
        return translations["en"][level_key[:2]]
    return ""
