import os
from pathlib import Path  # восстановлен импорт
import tempfile
from google.cloud import texttospeech

# ✅ Устанавливаем путь к JSON-ключу Google TTS
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "google-speech-key.json")  # читаем путь из переменной окружения

# ✅ Глобальная карта скорости по уровню
LEVEL_SPEED = {
    "A0": 0.8,
    "A1": 0.85,
    "A2": 0.9,
    "B1": 1.0,
    "B2": 1.0,
    "C1": 1.05,
    "C2": 1.1,
}

# ✅ МУЖСКИЕ голоса по умолчанию, fallback — женский
VOICE_SELECTION = {
    "en-US": ["en-US-Wavenet-D", "en-US-Wavenet-C"],
    "fr-FR": ["fr-FR-Wavenet-B", "fr-FR-Wavenet-A"],
    "de-DE": ["de-DE-Wavenet-B", "de-DE-Wavenet-A"],
    "es-ES": ["es-ES-Wavenet-B", "es-ES-Wavenet-A"],
    "ru-RU": ["ru-RU-Wavenet-B", "ru-RU-Wavenet-A"],
    "sv-SE": ["sv-SE-Wavenet-A", "sv-SE-Wavenet-D"]  # ✅ сначала мужской, потом fallback-женский
}

def synthesize_voice(text: str, lang: str, level: str) -> str:
    client = texttospeech.TextToSpeechClient()

    voice_names = VOICE_SELECTION.get(lang, ["en-US-Wavenet-D"])
    for voice_name in voice_names:
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)

            voice = texttospeech.VoiceSelectionParams(
                language_code=lang,
                name=voice_name
            )

            speaking_rate = LEVEL_SPEED.get(level.upper(), 1.0)

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.OGG_OPUS,
                speaking_rate=speaking_rate
            )

            # ✅ Вернули твой стиль: отдельное создание synthesis_input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as out:
                out.write(response.audio_content)
                return str(out.name)
        except Exception as e:
            print(f"[TTS fallback] Ошибка с голосом {voice_name}: {e}")
            continue

    raise RuntimeError("No available TTS voice for the selected language.")
