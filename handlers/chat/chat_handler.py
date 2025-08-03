import os
import tempfile
import openai
from telegram import Update
from telegram.ext import ContextTypes

from components.gpt_client import ask_gpt
from handlers.chat.prompt_templates import get_system_prompt  # ✨ актуализирован импорт
from components.voice import synthesize_voice
from components.mode import MODE_SWITCH_MESSAGES, get_mode_keyboard
from state.session import user_sessions
from components.levels import get_rules_by_level
from components.triggers import CREATOR_TRIGGERS, MODE_TRIGGERS

MAX_HISTORY_LENGTH = 40

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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}

    session = user_sessions[chat_id]
    session.setdefault("interface_lang", "en")
    session.setdefault("target_lang", "en")
    session.setdefault("level", "A2")
    session.setdefault("mode", "text")

    message_text = update.message.text or ""

    # === Универсальная обработка триггеров ===
    import re
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

    # --- Продолжаем обычную обработку ---

    # История переписки
    history = session.setdefault("history", [])

    interface_lang = session["interface_lang"]
    target_lang = session["target_lang"]
    level = session["level"]
    mode = session["mode"]

    style = session.get("style", "casual")
    print("DEBUG session:", session)
    print("DEBUG get_system_prompt:", style, level, interface_lang, target_lang, mode)
    system_prompt = get_system_prompt(style, level, interface_lang, target_lang, mode)

    # Исторический prompt + последнее сообщение
    prompt = [{"role": "system", "content": system_prompt}]
    for msg in history:
        prompt.append(msg)
    prompt.append({"role": "user", "content": message_text})

    # Генерация ответа через GPT
    assistant_reply = await ask_gpt(prompt, "gpt-4o")

    # Добавление в историю
    history.append({"role": "user", "content": message_text})
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

            # 🗣️ Дублируем текстом + перевод при необходимости
            if level == "A0":
                await context.bot.send_message(chat_id=chat_id, text=f"{assistant_reply}\n\n 💌")
            elif level in ["A1", "A2"]:
                await context.bot.send_message(chat_id=chat_id, text=assistant_reply)
        except Exception as e:
            print(f"[Ошибка отправки голоса] {e}")
    else:
        await update.message.reply_text(assistant_reply)

# ✨ Главное изменение: вся обработка триггеров теперь вынесена до отправки запроса в GPT и не вложена в другие циклы/блоки.
