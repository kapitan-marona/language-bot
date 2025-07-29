# components/voice.py
from pathlib import Path
from google.cloud import texttospeech
import tempfile
import os

# Скорость говора в зависимости от уровня
LEVEL_SPEED = {
    "A0": 0.8,
    "A1": 0.85,
    "A2": 0.9,
    "B1": 1.0,
    "B2": 1.0,
    "C1": 1.05,
    "C2": 1.1,
}

def synthesize_voice(text: str, lang: str, level: str) -> str:
    client = texttospeech.TextToSpeechClient()

    voice = texttospeech.VoiceSelectionParams(
        language_code=lang,
        ssml_gender=texttospeech.SsmlVoiceGender.MALE
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.OGG_OPUS,
        speaking_rate=LEVEL_SPEED.get(level.upper(), 1.0)
    )

    synthesis_input = texttospeech.SynthesisInput(text=text)

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as out:
        out.write(response.audio_content)
        return str(out.name)
