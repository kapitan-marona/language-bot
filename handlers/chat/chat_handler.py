import os
import time
import random
import re
from telegram import Update
from telegram.ext import ContextTypes

from components.gpt_client import ask_gpt
from components.voice import synthesize_voice
from components.mode import MODE_SWITCH_MESSAGES, get_mode_keyboard
from state.session import user_sessions
from handlers.chat.prompt_templates import START_MESSAGE, MATT_INTRO, INTRO_QUESTIONS
from handlers.chat.system_prompts import get_system_prompt  # <-- system prompt для GPT
from components.levels import get_rules_by_level
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

# --- Онбординг ---
async def send_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    interface_lang = session.get("interface_lang", "ru")
    await context.bot.send_message(chat_id=chat_id, text=START_MESSAGE.get(interface_lang, START_MESSAGE['en']))
    # Здесь твой вызов кнопок (выбора языка, уровня, стиля)
    # Например: await send_language_level_style_prompt(update, context)
    # После завершения онбординга — приветствие и вовлекающий вопрос:
    await context.bot.send_message(chat_id=chat_id, text=MATT_INTRO.get(interface_lang, MATT_INTRO['en']))
    target_lang = session.get("target_lang", interface_lang)
    question = random.choice(INTRO_QUESTIONS.get(target_lang, INTRO_QUESTIONS['en']))
    await context.bot.send_message(chat_id=chat_id, text=question)

# --- Главный message handler ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})

    # --- RATE LIMITING ---
    now = time.time()
    last_time = session.get("last_message_time", 0)
    if now - last_time < RATE_LIMIT_SECONDS:
        await context.bot.send_message(chat_id=chat_id, text="⏳ Погоди, думаю 🙂")
        return
    session["last_message_time"] = now

    try:
        # --- session defaults ---
        session.setdefault("interface_lang", "en")
        session.setdefault("target_lang", "en")
        session.setdefault("level", "A2")
        session.setdefault("mode", "text")
        session.setdefault("style", "casual")
        message_text = update.message.text or ""

        # === Универсальная обработка триггеров ===
        user_text_norm = re.sub(r'[^\w\s]', '', message_text.lower())
        lang = session.get("interface_lang", "en")

        # --- Переключение режима по тексту (voice/text) ---
        if any(trigger in user_text_norm for trigger in MODE_TRIGGERS["voice"]):
            session["mode"] = "voice"
            msg = MODE_SWITCH_MESSAGES["voice"].get(lang, MODE_SWITCH_MESSAGES["voice"]["en"])
            await update.message.reply_text(msg, reply_markup=get_mode_keyboard("voice"))
            return

        if any(trigger in user_text_norm for trigger in MODE_TRIGGERS["text"]):
            session["mode"] = "text"
            msg = MODE_SWITCH_MESSAGES["text"].get(lang, MODE_SWITCH_MESSAGES["text"]["en"])
            await update.message.reply_text(msg, reply_markup=get_mode_keyboard("text"))
            return

        # --- Обработка запроса про создателя/разработчика ---
        found_trigger = False
        for trig in CREATOR_TRIGGERS.get(lang, CREATOR_TRIGGERS["en"]):
            if trig in user_text_norm:
                found_trigger = True
                break

        if found_trigger:
            if lang == "ru":
                reply_text = "🐾 Мой создатель — @marrona! Для обратной связи и предложений к сотрудничеству обращайся прямо к ней. 🌷"
            else:
                reply_text = "🐾 My creator is @marrona! For feedback or collaboration offers, feel free to contact her directly. 🌷"
            await update.message.reply_text(reply_text)
            return

        # --- Переписка с GPT ---
        history = session.setdefault("history", [])
        interface_lang = session["interface_lang"]
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
