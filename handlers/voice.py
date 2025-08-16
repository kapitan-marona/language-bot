import os
import tempfile
import base64
import subprocess
from telegram import Update
from telegram.ext import ContextTypes
from config import client
from google.cloud import texttospeech
from .constants import LANG_CODES, WHISPER_SUPPORTED_LANGS, UNSUPPORTED_LANGUAGE_MESSAGE

# ✨ Настройка предпочтительных голосов
PREFERRED_VOICES = {
    "ru": "ru-RU-Wavenet-B",
    "en": "en-US-Wavenet-D",
    "de": "de-DE-Standard-A",
    "fr": "fr-FR-Wavenet-B",
    "es": "es-ES-Wavenet-A",
    "pt": "pt-BR-Wavenet-A",
    "it": "it-IT-Wavenet-B",
    "no": "nb-NO-Standard-A",
    "sv": "sv-SE-Standard-A",
    "fi": "fi-FI-Standard-A",
}

async def speak_and_reply(text: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    learn_lang = context.user_data.get("learn_lang", "English")
    lang_code = LANG_CODES.get(learn_lang, "en")
    lang_root = lang_code.split("-")[0]
    voice_name = PREFERRED_VOICES.get(lang_root)

    key_b64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_BASE64")
    if key_b64:
        import json
        key_json = base64.b64decode(key_b64).decode("utf-8")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as key_file:
            key_file.write(key_json.encode("utf-8"))
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_file.name

    client_tts = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice_params = texttospeech.VoiceSelectionParams(
        language_code=lang_code,
        name=voice_name or "",
        ssml_gender=texttospeech.SsmlVoiceGender.MALE,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
    )

    response = client_tts.synthesize_speech(
        input=synthesis_input,
        voice=voice_params,
        audio_config=audio_config,
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as out:
        out.write(response.audio_content)
        temp_file_name = out.name

    with open(temp_file_name, "rb") as audio_file:
        await update.message.reply_voice(audio_file, caption=text)

    os.remove(temp_file_name)

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    learn_lang = context.user_data.get("learn_lang", "English")
    lang_code = LANG_CODES.get(learn_lang, "en")

    if lang_code not in WHISPER_SUPPORTED_LANGS:
        await update.message.reply_text(UNSUPPORTED_LANGUAGE_MESSAGE.get(
            context.user_data.get("language", "English"),
            "Voice recognition is not supported for this language. Please use text input."
        ))
        return

    voice = update.message.voice
    if not voice:
        await update.message.reply_text("Не удалось получить голосовое сообщение.")
        return

    file = await context.bot.get_file(voice.file_id)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_ogg:
        await file.download_to_drive(temp_ogg.name)
        ogg_path = temp_ogg.name

    wav_path = ogg_path.replace(".ogg", ".wav")
    subprocess.run(["ffmpeg", "-i", ogg_path, "-ar", "16000", "-ac", "1", wav_path])

    try:
        with open(wav_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
                language=lang_code
            )
    except Exception as e:
        await update.message.reply_text("Произошла ошибка при распознавании речи. Попробуйте позже.")
        return
    finally:
        os.remove(ogg_path)
        os.remove(wav_path)

    # 💡 Импортируем chat внутри функции — избегаем циклического импорта
    from .chat.chat_handler import chat
    await chat(update, context, user_text_override=transcript.strip())
