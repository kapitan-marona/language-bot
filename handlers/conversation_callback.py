from telegram import Update
from telegram.ext import ContextTypes
from components.levels import get_level_keyboard, LEVEL_PROMPT
from components.language import get_target_language_keyboard, TARGET_LANG_PROMPT
from components.style import get_style_keyboard, STYLE_PROMPT, get_intro_by_level_and_style
from state.session import user_sessions


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data

    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}

    if data.startswith("lang_"):
        lang_code = data.split("_")[1]
        user_sessions[chat_id]["interface_lang"] = lang_code

        prompt = TARGET_LANG_PROMPT.get(lang_code, TARGET_LANG_PROMPT["en"])
        await query.message.reply_text(prompt, reply_markup=get_target_language_keyboard())

    elif data.startswith("target_"):
        target_code = data.split("_")[1]
        user_sessions[chat_id]["target_lang"] = target_code

        interface_lang = user_sessions[chat_id].get("interface_lang", "en")
        level_prompt = LEVEL_PROMPT.get(interface_lang, LEVEL_PROMPT["en"])
        await query.message.reply_text(level_prompt, reply_markup=get_level_keyboard())

    elif data.startswith("level_"):
        level_code = data.split("_")[1]
        user_sessions[chat_id]["level"] = level_code

        interface_lang = user_sessions[chat_id].get("interface_lang", "en")
        prompt = STYLE_PROMPT.get(interface_lang, STYLE_PROMPT["en"])
        await query.message.reply_text(prompt, reply_markup=get_style_keyboard())

    elif data.startswith("style_"):
        style_code = data.split("_")[1]
        user_sessions[chat_id]["style"] = style_code

        session = user_sessions[chat_id]
        level = session.get("level", "A0")
        interface_lang = session.get("interface_lang", "en")

        # Приветствие от Matt после выбора стиля
        intro = get_intro_by_level_and_style(level, style_code, interface_lang)
        await query.message.reply_text(intro)
