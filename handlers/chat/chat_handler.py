import os
import time
import random
import re
import tempfile
from telegram import Update
from telegram.ext import ContextTypes
from config.config import ADMINS

from components.gpt_client import ask_gpt
from components.voice import synthesize_voice, recognize_voice  # не забудь импорт!
from components.mode import MODE_SWITCH_MESSAGES, get_mode_keyboard
from state.session import user_sessions
from handlers.chat.prompt_templates import get_system_prompt, START_MESSAGE, MATT_INTRO, INTRO_QUESTIONS
from components.triggers import CREATOR_TRIGGERS, MODE_TRIGGERS

MAX_HISTORY_LENGTH = 40
RATE_LIMIT_SECONDS = 1.5

LANGUAGE_CODES = {
    "en": "en-US",
    "fr": "fr-FR",
    "de": "de-DE",
    "es": "es-ES",
    "ru": "ru-RU",
    "sv": "sv-SE",
    "fi": "fi-FI"
}

def get_greeting_name(lang: str) -> str:
    return "Matt" if lang == "en" else "Мэтт"

# --- Главный message handler ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})

    defaults = {
        "interface_lang": "en",
        "target_lang": "en",
        "level": "A2",
        "mode": "text",
        "style": "casual",
    }
    for k, v in defaults.items():
        session.setdefault(k, v)

    print("SESSION DEBUG:", session)  # временно

    # --- RATE LIMITING ---
    now = time.time()
    last_time = session.get("last_message_time", 0)
    if now - last_time < RATE_LIMIT_SECONDS:
        await context.bot.send_message(chat_id=chat_id, text="⏳ Погоди, думаю 🙂")
        return
    session["last_message_time"] = now

    try:
        # --- Обработка голосовых сообщений ---
        if getattr(update.message, "voice", None):
            voice_file = await context.bot.get_file(update.message.voice.file_id)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_voice:
                await voice_file.download_to_drive(tmp_voice.name)
                voice_path = tmp_voice.name

            recognized_text = recognize_voice(voice_path, session.get("interface_lang", "en"))
            print(f"[ASR] '{recognized_text}'")  # лог для отладки

            if not recognized_text:
                await context.bot.send_message(chat_id=chat_id, text="Не удалось распознать голос 😔 Попробуй ещё раз!")
                return
            message_text = recognized_text
        else:
            message_text = update.message.text or ""

        # === Универсальная обработка триггеров ===
        user_text_norm = re.sub(r'[^\w\s]', '', message_text.lower())
        interface_lang = session.get("interface_lang", "en")

        # --- Переключение режима по тексту (voice/text) ---
        if any(trigger in user_text_norm for trigger in MODE_TRIGGERS["voice"]):
            session["mode"] = "voice"
            msg = MODE_SWITCH_MESSAGES["voice"].get(interface_lang, MODE_SWITCH_MESSAGES["voice"]["en"])
            await update.message.reply_text(msg, reply_markup=get_mode_keyboard("voice", interface_lang))
            return

        if any(trigger in user_text_norm for trigger in MODE_TRIGGERS["text"]):
            session["mode"] = "text"
            msg = MODE_SWITCH_MESSAGES["text"].get(interface_lang, MODE_SWITCH_MESSAGES["text"]["en"])
            await update.message.reply_text(msg, reply_markup=get_mode_keyboard("text", interface_lang))
            return

        # --- Обработка запроса про создателя/разработчика ---
        found_trigger = False
        for trig in CREATOR_TRIGGERS.get(interface_lang, CREATOR_TRIGGERS["en"]):
            if trig in user_text_norm:
                found_trigger = True
                break

        if found_trigger:
            if interface_lang == "ru":
                reply_text = "🐾 Мой создатель — @marrona! Для обратной связи и предложений к сотрудничеству обращайся прямо к ней. 🌷"
            else:
                reply_text = "🐾 My creator is @marrona! For feedback or collaboration offers, feel free to contact her directly. 🌷"
            await update.message.reply_text(reply_text)
            return

        # --- Переписка с GPT ---
        history = session.setdefault("history", [])
        target_lang = session["target_lang"]
        level = session["level"]
        mode = session["mode"]
        style = session["style"]

        # --- Формируем system prompt ---
        system_prompt = get_system_prompt(style, level, interface_lang, target_lang, mode)
        prompt = [{"role": "system", "content": system_prompt}]
        for msg in history:
            prompt.append(msg)
        prompt.append({"role": "user", "content": message_text})

        assistant_reply = await ask_gpt(prompt, "gpt-4o")

        # --- История переписки ---
        history.append({"role": "user", "content": message_text})
        history.append({"role": "assistant", "content": assistant_reply})
        if len(history) > MAX_HISTORY_LENGTH:
            history.pop(0)

        # --- Ответ: текст или голос ---
        if mode == "voice":
            voice_path = synthesize_voice(assistant_reply, LANGUAGE_CODES.get(target_lang, "en-US"), level)
            try:
                with open(voice_path, "rb") as vf:
                    await context.bot.send_voice(chat_id=chat_id, voice=vf)
                if level == "A0":
                    await context.bot.send_message(chat_id=chat_id, text=f"{assistant_reply}\n\n 💌")
                elif level in ["A1", "A2"]:
                    await context.bot.send_message(chat_id=chat_id, text=assistant_reply)
            except Exception as e:
                print(f"[Ошибка отправки голоса] {e}")
                await context.bot.send_message(chat_id=chat_id, text="⚠️ Не удалось отправить голосовое сообщение. Вот текст:\n" + assistant_reply)
        else:
            await update.message.reply_text(assistant_reply)

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Что-то пошло не так! Попробуй ещё раз или перезапусти бота командой /start.")
        print(f"[ОШИБКА в handle_message]: {e}")
