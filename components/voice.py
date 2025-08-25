from __future__ import annotations
import os
import re
import tempfile
import subprocess
import shutil
import logging
from typing import Tuple
from openai import OpenAI
from config.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

_LEVEL_SET = {"A0", "A1", "A2", "B1", "B2", "C1", "C2"}

# -------------------- текстовая предобработка для TTS --------------------

# Убираем эмодзи/пиктограммы, чтобы TTS их не «произносил»
_EMOJI_RE = re.compile(
    "[\U0001F1E6-\U0001F1FF"  # флаги
    "\U0001F300-\U0001F5FF"   # символы/пиктограммы
    "\U0001F600-\U0001F64F"   # смайлы
    "\U0001F680-\U0001F6FF"   # транспорт/символы
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "]+",
    flags=re.UNICODE
)

# Хвост в скобках (обычно перевод на языке интерфейса) — не озвучиваем
_PARENS_TAIL_RE = re.compile(r"\s*\([^()]*\)\s*$")

def _strip_emojis(text: str) -> str:
    return _EMOJI_RE.sub("", text or "")

def _strip_parenthesized_tail(text: str) -> str:
    return _PARENS_TAIL_RE.sub("", text or "").strip()

def _slowdown_by_level(text: str, level: str) -> str:
    """
    Замедляем речь расстановкой мягких пауз (пунктуация/эллипсис) для TTS.
    Исходный текст пользователю не меняется — только вход в TTS.
    """
    lvl = (level or "").upper()
    if lvl in ("C1", "C2"):
        return text  # нормальная скорость

    words = (text or "").split()
    if not words:
        return text

    if lvl == "A0":
        step, sep = 2, " … "      # очень короткие фразы
    elif lvl == "A1":
        step, sep = 3, ", "
    elif lvl == "A2":
        step, sep = 4, ", "
    elif lvl == "B1":
        step, sep = 6, ", "
    else:  # B2
        step, sep = 8, ", "

    chunks = [" ".join(words[i:i+step]) for i in range(0, len(words), step)]
    slowed = sep.join(chunks).strip()
    if slowed and not slowed.endswith((".", "!", "?")):
        slowed += "."
    return slowed

def _prepare_tts_text(raw: str, level: str, max_len: int = 4000) -> str:
    # 1) ТОЛЬКО основная часть на целевом языке (убираем перевод в скобках)
    base = _strip_parenthesized_tail(raw or "")
    # 2) Не озвучиваем эмодзи/пиктограммы
    base = _strip_emojis(base)
    # 3) Замедление по уровню (для TTS)
    base = _slowdown_by_level(base, level)
    # 4) Ограничим длину
    if len(base) > max_len:
        base = base[:max_len]
    return base

# -------------------- совместимость с текущими вызовами --------------------

def _normalize_style_level(style: str, level: str) -> Tuple[str, str]:
    """
    Если в параметр 'style' по ошибке прилетел уровень (A1..C2),
    а в 'level' — нормальный уровень пустой/что-то иное — аккуратно разрулим.
    """
    s = (style or "").strip()
    l = (level or "").strip() or "A2"
    if s in _LEVEL_SET:
        # synthesize_voice(..., language_code, level) — старый порядок аргументов
        return "casual", s
    return (s or "casual"), l

# -------------------- маппинг голосов по языкам --------------------

_LANG_TO_VOICE = {
    "en": "alloy",  # мужской, нейтральный
    "es": "echo",   # мужской
    "fr": "echo",   # мужской
    "de": "ash",    # мужской, четкая дикция
    "ru": "echo",   # мужской
    "sv": "alloy",  # мужской
    "fi": "echo",   # мужской
}

# -------------------- основная функция TTS --------------------

def synthesize_voice(text: str, language_code: str, style: str = "casual", level: str = "A2") -> str:
    """
    Генерирует озвучку с использованием OpenAI TTS (tts-1).
    Возвращает путь к файлу .ogg (Opus) — готов для Telegram voice.

    - Эмодзи и перевод в скобках не озвучиваем.
    - Скорость/паузы зависят от уровня (A0…C2).
    - Сначала просим opus (идеально для voice). Если не вышло — mp3 и (если есть ffmpeg) перекодируем в OGG/Opus.
    """
    if not client:
        logger.error("OPENAI_API_KEY is missing for TTS")
        return ""

    style, level = _normalize_style_level(style, level)
    prepared = _prepare_tts_text(text, level)

    # Выбор мужского голоса по языку (без случайности)
    lang_code = (language_code or "en").split("-")[0].lower()
    voice = _LANG_TO_VOICE.get(lang_code, "alloy")

    logger.info("TTS: voice=%s lang=%s style=%s level=%s", voice, language_code, style, level)

    tmp_path = None
    output_path = None
    try:
        # 1) Прямо просим OGG/Opus — это правильный формат для send_voice
        resp = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=prepared,
            response_format="opus",   # FIX: новый параметр
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as out_file:
            data = getattr(resp, "content", None)
            if isinstance(data, (bytes, bytearray)):
                out_file.write(data)
            elif hasattr(resp, "read"):
                out_file.write(resp.read())
            elif isinstance(resp, (bytes, bytearray)):
                out_file.write(resp)
            else:
                raise RuntimeError("TTS opus returned empty/unknown payload")
            tmp_path = out_file.name

        output_path = tmp_path
        logger.info("TTS done (opus): %s", output_path)
        return output_path

    except Exception:
        logger.exception("[TTS] opus path failed, trying mp3 fallback")

    # 2) Фолбэк: mp3 → при наличии ffmpeg перекодируем в OGG/Opus
    try:
        resp = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=prepared,
            response_format="mp3",     # FIX: новый параметр
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as out_mp3:
            data = getattr(resp, "content", None)
            if isinstance(data, (bytes, bytearray)):
                out_mp3.write(data)
            elif hasattr(resp, "read"):
                out_mp3.write(resp.read())
            elif isinstance(resp, (bytes, bytearray)):
                out_mp3.write(resp)
            else:
                raise RuntimeError("TTS mp3 returned empty/unknown payload")
            mp3_path = out_mp3.name

        if shutil.which("ffmpeg"):
            ogg_fixed = mp3_path.replace(".mp3", "_fixed.ogg")
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", mp3_path, "-c:a", "libopus", "-b:a", "32k", ogg_fixed],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                try:
                    os.remove(mp3_path)
                except Exception:
                    pass
                logger.info("TTS reencoded via ffmpeg: %s", ogg_fixed)
                return ogg_fixed
            except subprocess.CalledProcessError:
                logger.warning("FFMPEG reencode failed; dropping to text fallback")
        else:
            logger.warning("ffmpeg not found: cannot convert mp3→opus for Telegram voice")

        return ""  # без корректного ogg/opus лучше вернуть пусто — верхний код отправит текст

    except Exception:
        logger.exception("[TTS fallback mp3] failed")
        return ""

    finally:
        try:
            if tmp_path and output_path and tmp_path != output_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            logger.debug("Failed to remove temp TTS raw file")
