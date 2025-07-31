import os
import tempfile
import subprocess  # ✅ Добавлено
from pathlib import Path
from openai import OpenAI
from config.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def synthesize_voice(text: str, language_code: str, level: str) -> str:
    """
    Генерация озвучки с использованием OpenAI TTS (TTS-1).
    """
    style_to_voice = {
        "casual": "alloy",
        "business": "fable"
    }
    voice = style_to_voice.get(level.lower(), "alloy")

    speed = {
        "A0": 0.85,
        "A1": 0.9,
        "A2": 0.95,
        "B1": 1.0,
        "B2": 1.05,
        "C1": 1.1,
        "C2": 1.15,
    }.get(level.upper(), 1.0)

    print(f"🔊 [TTS] Генерируем голос '{voice}' ({language_code}, уровень {level}, скорость {speed})")

    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as out_file:
            out_file.write(response.content)
            out_path = out_file.name

        # ✅ Перекодировка через ffmpeg
        fixed_path = out_path.replace(".ogg", "_fixed.ogg")
        subprocess.run(["ffmpeg", "-y", "-i", out_path, "-c:a", "libopus", fixed_path], check=True)
        print("✅ [FFMPEG] Перекодировка завершена:", fixed_path)
        return fixed_path

    except Exception as e:
        print(f"[TTS Error] Ошибка при генерации речи: {e}")
        return ""
