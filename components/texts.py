LANGUAGES = [
    ("\U0001F1EC\U0001F1E7 English", "en"),
    ("\U0001F1EA\U0001F1F8 Español", "es"),
    ("\U0001F1E9\U0001F1EA Deutsch", "de"),
    ("\U0001F1F7\U0001F1FA Русский", "ru"),
    ("\U0001F1EB\U0001F1F7 Français", "fr"),
    ("\U0001F1F8\U0001F1EA Svenska", "sv"),
    ("\U0001F1EB\U0001F1EE Suomi", "fi"),
]

# 🟡 восстановлено: текст выбора целевого языка
TARGET_LANG_PROMPT = {
    "ru": "\U0001F30D Выбери язык, который хочешь изучать:",
    "en": "\U0001F30D Choose the language you want to learn:"
}

# 🟡 восстановлено: список поддерживаемых языков
SUPPORTED_LANGUAGES = [code for _, code in LANGUAGES]

# 🟡 восстановлено: тексты для промокодов
PROMO_ASK = {
    "ru": "У тебя есть промокод?\n\U0001F449 Введи его или напиши 'нет'",
    "en": "Do you have a promo code?\n\U0001F449 Enter it or type 'no'"
}

PROMO_SUCCESS = {
    "ru": "Промокод успешно активирован! \U0001F49A",
    "en": "Promo code successfully activated! \U0001F49A"
}

PROMO_FAIL = {
    "ru": "Проверь промокод, почему-то не работает \u26A0\uFE0F",
    "en": "Something’s wrong with the promo code \u26A0\uFE0F"
}

PROMO_ALREADY_USED = {
    "ru": "Промокод уже был активирован ранее \U0001F446",
    "en": "This promo code has already been activated \U0001F446"
}

STYLE_LABEL_PROMPT = {
    "ru": "Какой стиль тебе ближе? \U0001F60E",
    "en": "Which style fits you best? \U0001F60E"
}


def get_language_keyboard():
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton  # может быть адаптировано
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for name, code in LANGUAGES:
        keyboard.add(KeyboardButton(name))
    return keyboard


def get_target_language_keyboard(native_lang_code, user_profile=None):
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton  # может быть адаптировано
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

    allowed_langs = LANGUAGES

    # 🟡 если промокод ограничивает — фильтруем только английский
    if user_profile and user_profile.get("promo_type") == "english_only":
        allowed_langs = [(name, code) for name, code in LANGUAGES if code == "en"]

    # 🟡 исключаем родной язык из списка
    for name, code in allowed_langs:
        if code != native_lang_code:
            keyboard.add(KeyboardButton(name))
    return keyboard
