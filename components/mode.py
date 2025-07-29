# components/mode.py
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def get_mode_keyboard(current_mode: str) -> InlineKeyboardMarkup:
    if current_mode == "voice":
        label = "💬 Text Mode"
        data = "mode_text"
    else:
        label = "🎷 Voice Mode"
        data = "mode_voice"

    keyboard = [[InlineKeyboardButton(label, callback_data=data)]]
    return InlineKeyboardMarkup(keyboard)

MODE_SWITCH_MESSAGES = {
    "voice": {
        "en": "👌 I'll send you voice messages now.",
        "ru": "👌 Теперь я буду отвечать голосом.",
    },
    "text": {
        "en": "👍 Back to text replies.",
        "ru": "👍 Возвращаюсь к текстовым ответам.",
    },
    "prompt": {
        "en": "Would you like me to speak? You can switch to Voice Mode 🎷.",
        "ru": "Хочешь, чтобы я заговорил? Переключись в голосовой режим 🎷.",
    },
}
