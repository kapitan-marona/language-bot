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
