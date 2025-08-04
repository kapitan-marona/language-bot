TEXTS = {
    "promo_ask": {
        "ru": "🔑 У тебя есть промокод?\n\nЕсли да — просто отправь его сюда.\nЕсли нет — напиши \"нет\", и поехали дальше!",
        "en": "🔑 Do you have a promo code?\n\nIf yes — just send it here.\nIf not — type \"no\" and let's move on!"
    },
    "promo_success": {
        "ru": "Промокод успешно активирован! 💚",
        "en": "Promo code successfully activated! 💚"
    },
    "promo_fail": {
        "ru": "Проверь промокод — что-то не сработало. ⚠️",
        "en": "Please check the promo code — something went wrong. ⚠️"
    },
    "promo_already_used": {
        "ru": "Ты уже активировал промокод ранее.",
        "en": "You've already used a promo code."
    },
    "choose_target": {
        "ru": "Выбери язык, который хочешь изучать:",
        "en": "Choose the language you want to learn:"
    }
}


def t(key, lang):
    """
    Возвращает текст по ключу и языку, с fallback на английский.
    """
    return TEXTS.get(key, {}).get(lang, TEXTS.get(key, {}).get("en", ""))


# 🟡 Для совместимости с существующими переменными:
PROMO_ASK = TEXTS["promo_ask"]
PROMO_SUCCESS = TEXTS["promo_success"]
PROMO_FAIL = TEXTS["promo_fail"]
PROMO_ALREADY_USED = TEXTS["promo_already_used"]
