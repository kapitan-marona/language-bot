import os
import tempfile
import subprocess
from openai import OpenAI
from config.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def synthesize_voice(text: str, language_code: str, style: str = "casual", level: str = "A2") -> str:
    """
    Генерирует озвучку с использованием OpenAI TTS (TTS-1), с выбором голоса по стилю.
    """
    style_to_voice = {
        "casual": "alloy",        # 😎 Cool — разговорный стиль
        "business": "fable"       # 🤓 Бизнес/деловой стиль
    }
    voice = style_to_voice.get(style.lower(), "alloy")  # Выбор голоса по стилю, default = alloy

    print(f"🔊 [TTS] Генерируем голос '{voice}' ({language_code}, стиль {style})")

    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as out_file:
            out_file.write(response.content)
            out_path = out_file.name

        # Перекодировка через ffmpeg (важно для Telegram)
        fixed_path = out_path.replace(".ogg", "_fixed.ogg")
        subprocess.run(["ffmpeg", "-y", "-i", out_path, "-c:a", "libopus", fixed_path], check=True)
        print("✅ [FFMPEG] Перекодировка завершена:", fixed_path)
        return fixed_path

    except Exception as e:
        print(f"[TTS Error] Ошибка при генерации речи: {e}")
        return ""
