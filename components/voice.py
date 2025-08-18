# components/voice.py
from __future__ import annotations
import os
import tempfile
import logging
from pathlib import Path
from typing import Tuple
import asyncio

from openai import AsyncOpenAI
from config.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Асинхронный клиент OpenAI
client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

_LEVEL_SET = {"A0", "A1", "A2", "B1", "B2", "C1", "C2"}

def _normalize_style_level(style: str, level: str) -> Tuple[str, str]:
    """
    Если в параметр 'style' по ошибке прилетел уровень (A1..C2),
    а в 'level' — пусто/что-то иное — аккуратно разрулим.
    """
    s = (style or "").strip()
    l = (level or "").strip() or "A2"
    if s in _LEVEL_SET:
        return "casual", s
    return (s or "casual"), l

def _sanitize_tts_text(text: str, max_len: int = 4000) -> str:
    t = (text or "").strip()
    return t[:max_len] if len(t) > max_len else t

# Карта «мягких пауз» для низких уровней: мы НЕ меняем показываемый пользователю текст,
# только аудио-вариант, чтобы звучало медленнее/разборчивее.
LEVEL_SPEED = {
    "A0": 0.5, "A1": 0.5, "A2": 0.5,
    "B1": 0.7, "B2": 0.7,
    "C1": 0.9, "C2": 0.9,
}

def _with_soft_pauses(text: str, level: str) -> str:
    """
    Простая эвристика: для A0–B1 вставляем лёгкие паузы (запятые/многоточия)
    после коротких смысловых фраз, чтобы TTS звучал медленнее.
    Визуальный текст пользователю НЕ меняем — только аудио-вход.
    """
    spd = LEVEL_SPEED.get(level, 0.9)
    if spd >= 0.9:
        return text
    # максимально деликатно: меняем только пробелы между предложениями
    # и добавляем небольшие паузы после ~каждых 5–7 слов
    import re
    words = re.split(r"(\s+)", text)
    out, cnt, step = [], 0, 6 if spd >= 0.7 else 4
    for w in words:
        out.append(w)
        if w.strip() and not re.match(r"\s+", w):
            cnt += 1
            if cnt % step == 0:
                out.append(", ")
    return "".join(out)

# Подбор голоса по стилю
STYLE_TO_VOICE = {
    "casual": "alloy",
    "business": "fable",
}

async def synthesize_voice(text: str, language_code: str, style: str = "casual", level: str = "A2") -> str:
    """
    Асинхронно генерирует озвучку через OpenAI TTS и сохраняет сразу в OGG.
    Возвращает путь к готовому файлу (для send_voice).
    Никакого ffmpeg: полагаемся на OpenAI, format='ogg'.
    """
    if not client:
        logger.error("OPENAI_API_KEY is missing for TTS")
        return ""

    style, level = _normalize_style_level(style, level)
    clean_text = _sanitize_tts_text(text, max_len=4000)
    audio_text = _with_soft_pauses(clean_text, level)  # только для аудио

    voice = STYLE_TO_VOICE.get(style.lower(), "alloy")

    # Файл-назначение
    tmpdir = tempfile.gettempdir()
    out_path = Path(tmpdir) / f"matt_tts_{os.getpid()}_{next(tempfile._get_candidate_names())}.ogg"

    try:
        # Стримим прямо в файл (async)
        async with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",   # актуальная TTS-модель
            voice=voice,
            input=audio_text,
            format="ogg",              # сразу OGG, без ffmpeg
        ) as response:
            await response.stream_to_file(str(out_path))

        logger.info("TTS ready: %s (voice=%s lang=%s style=%s level=%s)", out_path, voice, language_code, style, level)
        return str(out_path)

    except Exception:
        logger.exception("[TTS Error] Ошибка при генерации речи")
        # на всякий случай удалим пустой файл
        try:
            if out_path.exists() and out_path.stat().st_size == 0:
                out_path.unlink(missing_ok=True)
        except Exception:
            pass
        return ""
