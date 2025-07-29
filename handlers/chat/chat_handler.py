from telegram import Update
from telegram.ext import ContextTypes

from components.gpt_client import ask_gpt
from components.levels import get_rules_by_level
from state.session import user_sessions


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_input = update.message.text

    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}

    session = user_sessions[chat_id]

    # Проверка на завершение начальных настроек
    required = ["interface_lang", "target_lang", "level"]
    if not all(key in session for key in required):
        await update.message.reply_text("⚠️ Пожалуйста, сначала выбери язык, который ты хочешь изучать, и уровень через /start.")
        return

    interface_lang = session["interface_lang"]
    target_lang = session["target_lang"]
    level = session["level"]
    style = session.get("style", "casual")

    # Выбор имени
    bot_name = "Мэтт" if interface_lang == "ru" else "Matt"

    # Генерация system prompt
    system_prompt = (
        f"You are {bot_name}, a witty and kind language learning assistant.\n"
        f"You help the user learn {target_lang.upper()}.\n"
        f"You speak only in {target_lang.upper()}.\n"
        f"User level: {level}\n"
        f"User interface language: {interface_lang.upper()}\n"
        f"Your tone is {style}, curious and respectful.\n"
        f"{get_rules_by_level(level, interface_lang)}\n"
        f"Ask the user questions. Correct mistakes gently. Encourage them!"
    )

    # История сообщений
    history = session.get("history", [])
    history.append({"role": "user", "content": user_input})

    # Список сообщений
    messages = [{"role": "system", "content": system_prompt}] + history

    try:
        reply = ask_gpt(messages)
        history.append({"role": "assistant", "content": reply})
        session["history"] = history[-40:]  # ограничение в 40 сообщений
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("⚠️ Ошибка при обращении к GPT.")
        print(f"[GPT ERROR]: {e}")
