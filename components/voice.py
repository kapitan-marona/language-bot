import os
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

def _normalize_style_level(style: str, level: str) -> Tuple[str, str]:
    """
    Если в параметр 'style' по ошибке прилетел уровень (A1..C2),
    а в 'level' — нормальный уровень пустой/что-то иное — аккуратно разрулим.
    """
    s = (style or "").strip()
    l = (level or "").strip() or "A2"
    if s in _LEVEL_SET:
        # значит, вызов был synthesize_voice(..., language_code, level)
        # переставим местами: level = s, style = 'casual'
        return "casual", s
    return (s or "casual"), l

def _sanitize_tts_text(text: str, max_len: int = 4000) -> str:
    t = (text or "").strip()
    return t[:max_len] if len(t) > max_len else t

def synthesize_voice(text: str, language_code: str, style: str = "casual", level: str = "A2") -> str:
    """
    Генерирует озвучку с использованием OpenAI TTS (TTS-1), с выбором голоса по стилю.
    Возвращает путь к .ogg (или к файлу-результату), готовому для отправки в Telegram.
    Перекодировка через ffmpeg выполняется ТОЛЬКО если ffmpeg доступен в системе.
    """
    if not client:
        logger.error("OPENAI_API_KEY is missing for TTS")
        return ""

    style, level = _normalize_style_level(style, level)
    text = _sanitize_tts_text(text, max_len=4000)

    style_to_voice = {
        "casual": "alloy",        # 😎 Разговорный стиль
        "business": "fable"       # 🤓 Деловой стиль
    }
    voice = style_to_voice.get(style.lower(), "alloy")

    logger.info("TTS: voice=%s lang=%s style=%s level=%s", voice, language_code, style, level)

    tmp_path = None
    output_path = None
    try:
        # Генерация TTS
        resp = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as out_file:
            out_file.write(resp.content)
            tmp_path = out_file.name

        # Попробуем перекодировать ТОЛЬКО если есть ffmpeg (например, чтобы гарантировать opus)
        if shutil.which("ffmpeg"):
            fixed_path = tmp_path.replace(".ogg", "_fixed.ogg")
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", tmp_path, "-c:a", "libopus", fixed_path],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                output_path = fixed_path
                logger.info("TTS reencoded via ffmpeg: %s", fixed_path)
            except subprocess.CalledProcessError:
                logger.warning("FFMPEG reencode failed; using original: %s", tmp_path)
                output_path = tmp_path
        else:
            # ffmpeg недоступен — используем исходный файл
            output_path = tmp_path

        logger.info("TTS done: %s", output_path)
        return output_path

    except Exception:
        logger.exception("[TTS Error] Ошибка при генерации речи")
        return ""
    finally:
        # Если делали перекодировку и она успешна — удалим сырой файл
        try:
            if output_path and tmp_path and output_path != tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            logger.debug("Failed to remove temp TTS raw file")
