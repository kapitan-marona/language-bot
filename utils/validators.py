import re

# Разрешаем двузначные ISO-коды языков (en, ru, fr, es, de, sv, fi)
LANG_CODE_RE = re.compile(r"^(en|ru|fr|es|de|sv|fi)$")

def parse_callback(data: str, expected_prefix: str) -> str | None:
    if not data or ":" not in data:
        return None
    prefix, value = data.split(":", 1)
    if prefix != expected_prefix:
        return None
    return value.strip() or None

def is_lang_code(value: str) -> bool:
    return bool(value and LANG_CODE_RE.match(value))

def sanitize_user_text(text: str, max_len: int = 2000) -> str:
    text = (text or "").strip()
    if len(text) > max_len:
        text = text[:max_len]
    return text
