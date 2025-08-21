# components/triggers.py
import re

# --- Триггеры про создателя / контакты ---
CREATOR_TRIGGERS = {
    "ru": [
        "кто тебя создал", "создатель", "автор", "разработчик",
        "куда отзыв", "кому написать", "как связаться с автором",
        "как связаться с разработчиком", "написать разработчику"
    ],
    "en": [
        "who made you", "who created you", "your creator", "your developer",
        "who is your author", "how to contact author", "feedback", "contact developer"
    ],
    "es": [
        "quien te creó", "quien te hizo", "autor", "creador", "desarrollador", "cómo contactar al autor"
    ],
    "de": [
        "wer hat dich erstellt", "entwickler", "autor", "kontakt zum entwickler", "feedback geben"
    ],
    "fr": [
        "qui t'a créé", "ton créateur", "ton développeur", "contacter le développeur", "laisser un avis"
    ],
    "sv": [
        "vem skapade dig", "din skapare", "din utvecklare", "kontakta utvecklaren", "ge feedback"
    ],
}

# --- Триггеры переключения режима (короткие команды) ---
MODE_TRIGGERS = {
    "voice": [
        "голос", "voice"
    ],
    "text": [
        "текст", "text"
    ],
}

# --- Одноразовая озвучка последнего ответа ассистента ---
SAY_ONCE_TRIGGERS = {
    "ru": ["озвучь", "произнеси", "скажи вслух"],
    "en": ["voice it", "say it", "pronounce it", "read it aloud"],
    "es": ["léelo en voz alta", "pronúncialo"],
    "de": ["sprich es", "lies es vor"],
    "fr": ["dis-le", "lis-le à voix haute"],
    "sv": ["säga det", "läs upp det"],
    "fi": ["sano se ääneen", "lue se ääneen"],
}

# ============================
# Нормализация и строгие проверки
# ============================

def _norm(s: str) -> str:
    """Нормализует текст: нижний регистр, без пунктуации/лишних пробелов."""
    return re.sub(r"[^\w\s]", "", (s or "").lower()).strip()

# Предвычислим нормализованные множества для O(1) проверки
_MODE_TRIGGERS_NORM = {
    kind: {_norm(x) for x in phrases}
    for kind, phrases in MODE_TRIGGERS.items()
}

def is_strict_mode_trigger(user_text: str, kind: str) -> bool:
    """
    Истинный триггер — когда НОРМАЛИЗОВАННЫЙ текст сообщения
    ТОЧНО равен одной из фраз-триггеров (короткая команда).
    Пример: 'голос' -> да; 'запиши голосовое' -> нет.
    """
    norm = _norm(user_text)
    return norm in _MODE_TRIGGERS_NORM.get(kind, set())

def is_strict_say_once_trigger(user_text: str, interface_lang: str) -> bool:
    """
    Разовая озвучка: команда считается истинной, если НОРМАЛИЗОВАННЫЙ текст
    равен одной из коротких фраз в словаре SAY_ONCE_TRIGGERS для языка интерфейса
    (плюс запасной английский).
    """
    norm = _norm(user_text)
    phrases = SAY_ONCE_TRIGGERS.get(interface_lang, []) + SAY_ONCE_TRIGGERS.get("en", [])
    return norm in {_norm(p) for p in phrases}

__all__ = [
    "CREATOR_TRIGGERS",
    "MODE_TRIGGERS",
    "SAY_ONCE_TRIGGERS",
    "is_strict_mode_trigger",
    "is_strict_say_once_trigger",
]
