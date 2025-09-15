# components/tts_cache.py
import hashlib
import os
from typing import Optional

def _cache_dir() -> str:
    base = os.environ.get("BOT_TTS_CACHE_DIR", "./tmp/tts_cache")
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        base = "/tmp/tts_cache"
        os.makedirs(base, exist_ok=True)
    return base

def tts_cache_key(text: str, lang: str, level: str) -> str:
    h = hashlib.sha256(f"{lang}|{level}|{text}".encode("utf-8")).hexdigest()
    return h[:32]

def cached_tts_path(text: str, lang: str, level: str) -> Optional[str]:
    key = tts_cache_key(text, lang, level)
    ogg = os.path.join(_cache_dir(), f"{key}.ogg")
    return ogg if os.path.exists(ogg) else None

def store_tts_path(text: str, lang: str, level: str, path: str) -> str:
    # если источник уже ogg — просто сделаем hard copy
    dst = os.path.join(_cache_dir(), f"{tts_cache_key(text, lang, level)}.ogg")
    try:
        if os.path.abspath(path) != os.path.abspath(dst):
            with open(path, "rb") as src, open(dst, "wb") as out:
                out.write(src.read())
    except Exception:
        # кэш — best effort
        return path
    return dst
