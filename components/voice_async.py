# components/voice_async.py
import asyncio
import logging
import os

from typing import Optional
from config.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# --- Мы используем твою существующую синхронную функцию из components.voice ---
# Никакого самоимпорта: этот файл отдельный, поэтому всё ок.
try:
    from components.voice import synthesize_voice as _sync_synthesize_voice
except Exception as e:
    # Если вдруг модуль/функция не найдена — это реальная ошибка конфигурации проекта.
    logger.exception("Failed to import sync synthesize_voice from components.voice")
    raise

# ---- ASR (Whisper) клиенты ----
_openai_async_client = None
_openai_sync_client = None

try:
    from openai import AsyncOpenAI
    _openai_async_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
except Exception:
    _openai_async_client = None

if _openai_async_client is None:
    try:
        from openai import OpenAI
        _openai_sync_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
    except Exception:
        _openai_sync_client = None


async def speech_to_text_async(audio_path: str) -> str:
    """
    Безопасная async-обёртка Whisper ASR.
    Возвращает распознанный текст или "".
    """
    if not audio_path or not os.path.exists(audio_path):
        return ""

    # 1) Нативный async-клиент, если доступен
    if _openai_async_client:
        try:
            with open(audio_path, "rb") as f:
                resp = await _openai_async_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                )
            return (getattr(resp, "text", "") or "").strip()
        except Exception:
            logger.exception("[ASR] AsyncOpenAI failed")
            return ""

    # 2) Фолбэк: синхронный клиент в thread pool
    if _openai_sync_client:
        def _call() -> str:
            try:
                with open(audio_path, "rb") as f:
                    resp = _openai_sync_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                    )
                return (getattr(resp, "text", "") or "").strip()
            except Exception:
                logger.exception("[ASR] OpenAI sync failed")
                return ""
        return await asyncio.to_thread(_call)

    logger.error("[ASR] No OpenAI client available")
    return ""


async def synthesize_voice_async(text: str, language_code: str, level: str = "A2") -> str:
    """
    Async-обёртка над твоей синхронной TTS-функцией synthesize_voice(...).
    Ничего в её логике не меняем — просто уводим в thread pool.
    """
    def _call() -> str:
        try:
            # пробуем твою сигнатуру (style — опционален в твоей реализации)
            return _sync_synthesize_voice(text, language_code, level=level)
        except TypeError:
            # если сигнатура: (text, language_code, style, level)
            return _sync_synthesize_voice(text, language_code, style="casual", level=level)
        except Exception:
            logger.exception("[TTS] synthesize_voice failed")
            return ""

    path = await asyncio.to_thread(_call)
    if not path:
        raise RuntimeError("TTS returned empty path")
    return path
