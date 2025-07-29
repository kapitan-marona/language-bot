from telegram import Update
from telegram.ext import ContextTypes

from components.gpt_client import ask_gpt
from state.session import user_sessions


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_input = update.message.text

    # Создаём сессию при необходимости
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}

    session = user_sessions[chat_id]

    # Получаем настройки пользователя
    interface_lang = session.get("interface_lang", "en")
    target_lang = session.get("target_lang", "en")
    level = session.get("level", "A1")  # по умолчанию — beginner
    style = session.get("style", "casual")  # в будущем

    # Составляем system prompt на основе уровня и цели
    system_prompt = (
        f"You are a language learning assistant. "
        f"Speak to the user in {target_lang.upper()} only. "
        f"User level: {level}. "
        f"Be {style} and helpful. Correct mistakes gently."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    try:
        response = ask_gpt(messages)
        await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text("⚠️ Ошибка при обращении к GPT.")
        print(f"GPT error: {e}")
