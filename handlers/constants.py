# 🌐 Supported language codes for TTS and Whisper
LANG_CODES = {
    "English": "en",
    "French": "fr",
    "Spanish": "es",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Finnish": "fi",
    "Norwegian": "no",
    "Swedish": "sv",
    "Russian": "ru"
}

# 🧠 Whisper-supported languages (ISO codes)
WHISPER_SUPPORTED_LANGS = {
    "en", "fr", "es", "de", "it", "pt", "sv", "ru"
}

# 🚫 Voice recognition fallback messages
UNSUPPORTED_LANGUAGE_MESSAGE = {
    "Русский": (
        "Этот язык пока не поддерживается для распознавания речи. Вы можете продолжать использовать голосовой режим, "
        "но отправлять вопросы нужно в текстовом виде. Попробуйте голосовой ввод на клавиатуре — он преобразует вашу речь в текст, "
        "а бот ответит голосом!"
    ),
    "English": (
        "This language is not yet supported for voice recognition. You can keep using voice mode, but please send your questions as text. "
        "Try using voice input on your keyboard — it will convert your speech to text, and the bot will reply with voice!"
    )
}
