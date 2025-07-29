from telegram import Update
from telegram.ext import ContextTypes

from components.language import get_target_language_keyboard, TARGET_LANG_PROMPT
from components.levels import get_level_keyboard, LEVEL_PROMPT
from state.session import user_sessions


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data

    # Создаём или обновляем сессию для пользователя
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}

    # 1. Выбор языка интерфейса
    if data.startswith("lang_"):
        lang_code = data.split("_")[1]
        user_sessions[chat_id]["interface_lang"] = lang_code

        prompt = TARGET_LANG_PROMPT.get(lang_code, TARGET_LANG_PROMPT["en"])
        await query.message.reply_text(prompt, reply_markup=get_target_language_keyboard())

    # 2. Выбор изучаемого языка
    elif data.startswith("target_"):
        target_code = data.split("_")[1]
        user_sessions[chat_id]["target_lang"] = target_code

        interface_lang = user_sessions[chat_id].get("interface_lang", "en")
        level_prompt = LEVEL_PROMPT.get(interface_lang, LEVEL_PROMPT["en"])
        await query.message.reply_text(level_prompt, reply_markup=get_level_keyboard())

    # 3. Выбор уровня владения
    elif data.startswith("level_"):
        level_code = data.split("_")[1]
        user_sessions[chat_id]["level"] = level_code

        interface_lang = user_sessions[chat_id].get("interface_lang", "en")

        if interface_lang == "ru":
            confirmation = f"Уровень «{level_code.upper()}» выбран. 🚀"
        else:
            confirmation = f"Level «{level_code.upper()}» selected. 🚀"

        await query.message.reply_text(confirmation)

