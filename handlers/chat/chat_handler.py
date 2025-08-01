import os
import tempfile
import openai
from telegram import Update
from telegram.ext import ContextTypes

from components.gpt_client import ask_gpt
from handlers.chat.prompt_templates import get_system_prompt  # ✨ актуализирован импорт
from components.voice import synthesize_voice
from components.mode import MODE_SWITCH_MESSAGES
from state.session import user_sessions
from components.levels import get_rules_by_level


MAX_HISTORY_LENGTH = 40

LANGUAGE_CODES = {
    "en": "en-US",
    "fr": "fr-FR",
    "de": "de-DE",
    "es": "es-ES",
    "ru": "ru-RU",
    "sv": "sv-SE"
}

def get_greeting_name(lang: str) -> str:
    return "Matt" if lang == "en" else "Мэтт"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}

    session = user_sessions[chat_id]
    session.setdefault("interface_lang", "en")
    session.setdefault("target_lang", "en")
    session.setdefault("level", "A1")
    session.setdefault("style", "casual")
    session.setdefault("mode", "text")
    session.setdefault("history", [])

    interface_lang = session["interface_lang"]
    target_lang = session["target_lang"]
    level = session["level"]
    style = session.get("style", "casual").lower()
    mode = session["mode"]
    history = session["history"]

    # 🔊 Распознавание голоса (Whisper)
    if update.message.voice:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tf:
            await voice_file.download_to_drive(tf.name)
            audio_path = tf.name

        with open(audio_path, "rb") as f:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text"
            )
        os.remove(audio_path)
        user_input = transcript.strip()
        print("📝 [Whisper] Распознанный текст:", repr(user_input))
    else:
        user_input = update.message.text

    # 🚀 Триггеры на смену режима
    voice_triggers = ["скажи голосом", "включи голос", "озвучь", "произнеси", "скажи это", "как это звучит", "давай голосом"]
    text_triggers = ["вернись к тексту", "хочу текст", "пиши", "текстом"]

    if user_input:
        lowered = user_input.lower()
        if any(trigger in lowered for trigger in voice_triggers):
            session["mode"] = "voice"
            await update.message.reply_text(MODE_SWITCH_MESSAGES["voice"].get(interface_lang, "Voice mode activated."))
            return
        elif any(trigger in lowered for trigger in text_triggers):
            session["mode"] = "text"
            await update.message.reply_text(MODE_SWITCH_MESSAGES["text"].get(interface_lang, "Text mode activated."))
            return

    # 🔧 Генерация system prompt со стилевым подходом
    system_prompt = get_system_prompt(style)  # ✨ заменили прежнюю сборку system prompt

    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_input}]
    assistant_reply = await ask_gpt(messages)
    print("💬 [GPT] Ответ:", repr(assistant_reply))

    # ✅ Обновляем историю
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": assistant_reply})

    if len(history) > MAX_HISTORY_LENGTH:
        history.pop(0)

    # 📤 Отправка в зависимости от режима
    if mode == "voice":
        voice_path = synthesize_voice(assistant_reply, LANGUAGE_CODES.get(target_lang, "en-US"), level)
        print("🔊 [TTS] Файл озвучки:", voice_path)
        print("📁 Файл существует:", os.path.exists(voice_path))
        try:
            with open(voice_path, "rb") as vf:
                await context.bot.send_voice(chat_id=chat_id, voice=vf)

            # 🚣️ Дублируем текстом на A0 и A1-A2
            if level in ["A0", "A1", "A2"]:  # ✨ дублирование текста при voice-режиме
                await context.bot.send_message(chat_id=chat_id, text=assistant_reply)
        except Exception as e:
            print(f"[Ошибка отправки голоса] {e}")
    else:
        await update.message.reply_text(assistant_reply)
