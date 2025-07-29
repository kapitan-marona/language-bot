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

    # Проверка обязательных настроек
    required = ["interface_lang", "target_lang", "level", "style"]
    if not all(key in session for key in required):
        await update.message.reply_text("⚠️ Пожалуйста, сначала выбери язык, уровень и стиль общения через /start.")
        return

    interface_lang = session["interface_lang"]
    target_lang = session["target_lang"]
    level = session["level"]
    style = session["style"]

    # Имя
    bot_name = "Мэтт" if interface_lang == "ru" else "Matt"

    # Стиль общения
    if style == "casual":
        tone = (
            "You're relaxed, playful, and cheerful. You use slang, emojis, memes, "
            "and speak like a friendly buddy (e.g., 'mate', 'pal'). You joke often and express emotions clearly."
        )
    elif style == "business":
        tone = (
            "You're respectful, witty, and professional. You use polite and formal language, "
            "avoid slang, and limit emojis. You maintain distance like in a business setting, "
            "but you're not boring or robotic."
        )
    else:
        tone = "Be friendly and helpful."

    system_prompt = (
        f"Your name is {bot_name}. You're a language tutor helping the user learn {target_lang.upper()}.\n"
        f"You speak only in {target_lang.upper()}.\n"
        f"User level: {level}. Interface language: {interface_lang.upper()}.\n"
        f"{tone}\n"
        f"{get_rules_by_level(level, interface_lang)}\n"
        f"Ask questions based on user's messages. Gently correct their mistakes. Encourage them."
    )

    # История
    history = session.get("history", [])
    history.append({"role": "user", "content": user_input})

    messages = [{"role": "system", "content": system_prompt}] + history

    try:
        reply = ask_gpt(messages)
        history.append({"role": "assistant", "content": reply})
        session["history"] = history[-40:]
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("⚠️ Ошибка при обращении к GPT.")
        print(f"[GPT ERROR]: {e}")
