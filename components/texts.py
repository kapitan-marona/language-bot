LANGUAGES = [
    ("🇬🇧 English", "en"),
    ("🇪🇸 Español", "es"),
    ("🇩🇪 Deutsch", "de"),
    ("🇷🇺 Русский", "ru"),
    ("🇫🇷 Français", "fr"),
    ("🇸🇪 Svenska", "sv"),
    ("🇫🇮 Suomi", "fi"),
]

# 🟡 восстановлено: текст выбора целевого языка
TARGET_LANG_PROMPT = {
    "ru": "🌍 Выбери язык, который хочешь изучать:",
    "en": "🌍 Choose the language you want to learn:"
}

# 🟡 восстановлено: список поддерживаемых языков
SUPPORTED_LANGUAGES = [code for _, code in LANGUAGES]

# 🟡 восстановлено: тексты для промокодов
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
    "ru": "Промокод уже был активирован ранее ☝️",
    "en": "This promo code has already been activated ☝️"
}

STYLE_LABEL_PROMPT = {
    "ru": "Какой стиль тебе ближе? 😎",
    "en": "Which style fits you best? 😎"
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
