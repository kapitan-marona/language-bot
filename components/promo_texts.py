PROMO_ASK = {
    "ru": "У тебя есть промокод?\n👉 Введи его или напиши 'нет'",
    "en": "Do you have a promo code?\n👉 Enter it or type 'no'"
}
PROMO_SUCCESS = {
    "ru": "Промокод успешно активирован! 💚",
    "en": "Promo code successfully activated! 💚"
}
PROMO_FAIL = {
    "ru": "Проверь промокод, почему-то не работает ⚠️",
    "en": "Something’s wrong with the promo code ⚠️"
}
PROMO_ALREADY_USED = {
    "ru": "Промокод уже был активирован ранее 👆",
    "en": "This promo code has already been activated 👆"
}

# --- Promo status (короткие и дружелюбные ответы) --- 
PROMO_STATUS = {
    "not_activated": "🔑 У тебя пока нет активированного промокода",
    "permanent": "✨ Промокод активен, действует всегда",
    "timed_unknown": "⏳ Промокод активен, срок действия не определён",
    "expired": "⌛ Срок действия промокода закончился",
}

def promo_status_timed_left(days_left: int) -> str:
    """
    Дружелюбное короткое сообщение о действии промокода с корректным склонением.
    Пример: "⏳ Промокод активен: ещё 20 дней"
    """
    n = days_left % 100
    if 11 <= n <= 14:
        word = "дней"
    else:
        last = days_left % 10
        word = "день" if last == 1 else ("дня" if last in (2, 3, 4) else "дней")
    return f"⏳ Промокод активен: ещё {days_left} {word}"

# --- Header for unified promo message ---
PROMO_HEADER_TPL = {
    "ru": "Промокод {code}:",
    "en": "Promo code {code}:",
}

# --- Detailed lines (multiline body) for unified promo message ---
PROMO_DETAILS = {
    "ru": {
        "permanent_all":      "♾️ действует бессрочно\n🌐 открывает все языки",
        "english_only":       "♾️ действует бессрочно\n🇬🇧 открывает английский язык",
        # {days} и {days_word} подставляем в коде
        "timed_generic":      "⏳ действует ещё {days} {days_word}\n🌐 открывает все языки и возможности\n🕊️ без ограничений",
        "timed_end_of_month": "⏳ действует до конца месяца — ещё {days} {days_word}\n🌐 открывает все языки и возможности\n🕊️ без ограничений",
        "frau":               "🎓 действует до 26 октября\n🇩🇪🇬🇧 открывает немецкий и английский языки\n👩‍🏫 доступен для студентов и друзей школы Deutsch mit Frau Kloppertants",
        "not_active":         "🎟️ промокод не активирован\nℹ️ отправь: /promo <код>",
        "unknown_type":       "ℹ️ тип промокода не распознан",
    },
    "en": {
        "permanent_all":      "♾️ valid forever\n🌐 unlocks all languages",
        "english_only":       "♾️ valid forever\n🇬🇧 unlocks English only",
        # {days} and {days_word} substituted in code
        "timed_generic":      "⏳ valid for {days} {days_word} more\n🌐 unlocks all languages and features\n🕊️ no limits",
        "timed_end_of_month": "⏳ valid until the end of the month — {days} {days_word} left\n🌐 unlocks all languages and features\n🕊️ no limits",
        "frau":               "🎓 valid until October 26\n🇩🇪🇬🇧 unlocks German and English\n👩‍🏫 available for students and friends of the school Deutsch mit Frau Kloppertants",
        "not_active":         "🎟️ promo code not activated\nℹ️ send: /promo <code>",
        "unknown_type":       "ℹ️ promo type not recognized",
    },
}
