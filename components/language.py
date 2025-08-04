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
    "ru": "Выбери язык, который хочешь изучать:",
    "en": "Choose the language you want to learn:"
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
