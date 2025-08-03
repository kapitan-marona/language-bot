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

    # --- 🔽🔽🔽  Обработка запроса про создателя/разработчика  🔽🔽🔽 ---
    # Проверяем, не спрашивает ли пользователь "кто тебя создал", "кто твой разработчик" и т.д.
    import re

    # Список ключевых фраз на русском и английском
    creator_triggers_ru = [
        "кто тебя создал",
        "кто твой создатель",
        "кто твой разработчик",
        "кто тебя разработал",
        "кто тебя придумал",
        "как ты появился",
        "откуда ты взялся"
    ]
    creator_triggers_en = [
        "who created you",
        "who is your creator",
        "who is your developer",
        "who developed you",
        "who invented you",
        "how did you appear",
        "where did you come from"
    ]

    # Приводим текст к нижнему регистру и убираем знаки препинания для удобства поиска
    user_text_norm = re.sub(r'[^\w\s]', '', message_text.lower())

    # Определяем язык интерфейса для выбора ответа
    lang = session.get("interface_lang", "en")

    # Проверка на срабатывание одного из триггеров
    found_trigger = False
    if lang == "ru":
        for trig in creator_triggers_ru:
            if trig in user_text_norm:
                found_trigger = True
                break
    else:
        for trig in creator_triggers_en:
            if trig in user_text_norm:
                found_trigger = True
                break

    # Если триггер найден — отправляем специальный ответ и прекращаем дальнейшую обработку
    if found_trigger:
        if lang == "ru":
            reply_text = "🐾 Мой создатель — @marrona! Для обратной связи и предложений к сотрудничеству обращайся прямо к ней. 🌷"
        else:
            reply_text = "🐾 My creator is @marrona! For feedback or collaboration offers, feel free to contact her directly. 🌷"
        await update.message.reply_text(reply_text)
        return
    # --- 🔼🔼🔼  Конец блока обработки  🔼🔼🔼 ---

    # История переписки
    history = session.setdefault("history", [])

    interface_lang = session["interface_lang"]
    target_lang = session["target_lang"]
    level = session["level"]
    mode = session["mode"]

    style = session.get("style", "casual")
    system_prompt = get_system_prompt(style, level, interface_lang, mode)

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
