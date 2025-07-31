
import os
from telegram import Update
from telegram.ext import ContextTypes
from config.config import MAX_HISTORY_LENGTH
from components.voice import transcribe_voice, synthesize_voice
from components.language import LANGUAGE_CODES
from components.prompts import get_system_prompt
from services.gpt import ask_gpt
from state.session import user_sessions

# 🔁 Триггеры переключения режима
voice_triggers = ["скажи голосом", "включи голос", "озвучь", "произнеси", "скажи это", "как это звучит", "давай голосом"]
text_triggers = ["вернись к тексту", "хочу текст", "пиши", "текстом"]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id

    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}

    session = user_sessions[chat_id]
    interface_lang = session.get("interface_lang", "en")
    target_lang = session.get("target_lang", "en")
    level = session.get("level", "A1")
    style = session.get("style", "casual")
    mode = session.get("mode", "text")
    history = session.setdefault("history", [])

    user_input = None

    # 🎙 Голосовое сообщение
    if message.voice:
        voice_file = await context.bot.get_file(message.voice.file_id)
        file_path = f"temp/{chat_id}_voice.ogg"
        await voice_file.download_to_drive(file_path)
        transcript = transcribe_voice(file_path)
        user_input = transcript.strip()
        print("📝 [Whisper] Распознанный текст:", user_input)
    elif message.text:
        user_input = message.text.strip()

    if not user_input:
        return

    lowered = user_input.lower()
    if any(trigger in lowered for trigger in voice_triggers):
        session["mode"] = "voice"
        await message.reply_text("Voice mode activated.")
        return
    elif any(trigger in lowered for trigger in text_triggers):
        session["mode"] = "text"
        await message.reply_text("Text mode activated.")
        return

    # 🧠 Сбор system prompt и история
    system_prompt = get_system_prompt(style)
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_input}]
    assistant_reply = await ask_gpt(messages)
    print("💬 [GPT] Ответ:", repr(assistant_reply))

    # 📜 Обновление истории
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": assistant_reply})
    if len(history) > MAX_HISTORY_LENGTH:
        history.pop(0)

    # 🔁 Ответ в зависимости от режима
    if session.get("mode") == "voice":
        voice_path = synthesize_voice(assistant_reply, LANGUAGE_CODES.get(target_lang, "en-US"), level)
        if voice_path and os.path.exists(voice_path):
            try:
                with open(voice_path, "rb") as vf:
                    await context.bot.send_voice(chat_id=chat_id, voice=vf)
            except Exception as e:
                print(f"[Ошибка отправки голоса] {e}")
        await message.reply_text(assistant_reply)
    else:
        await message.reply_text(assistant_reply)
