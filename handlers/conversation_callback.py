from telegram import Update
from telegram.ext import ContextTypes
from components.levels import get_level_keyboard, LEVEL_PROMPT
from components.language import get_target_language_keyboard, TARGET_LANG_PROMPT
from components.mode import get_mode_keyboard, MODE_SWITCH_MESSAGES
from components.style import get_style_keyboard, get_intro_by_level_and_style, STYLE_PROMPT
from state.session import user_sessions

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data

    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}

    session = user_sessions[chat_id]

    # 🌐 Выбор языка интерфейса
    if data.startswith("lang_"):
        lang_code = data.split("_")[1]
        session["interface_lang"] = lang_code
        session["mode"] = "text"  # режим по умолчанию

        prompt = TARGET_LANG_PROMPT.get(lang_code, TARGET_LANG_PROMPT["en"])
        await query.message.reply_text(prompt, reply_markup=get_target_language_keyboard())

    # 🌍 Язык обучения
    elif data.startswith("target_"):
        target_code = data.split("_")[1]
        session["target_lang"] = target_code

        interface_lang = session.get("interface_lang", "en")
        level_prompt = LEVEL_PROMPT.get(interface_lang, LEVEL_PROMPT["en"])
        await query.message.reply_text(level_prompt, reply_markup=get_level_keyboard())

    # 📒 Уровень
    elif data.startswith("level_"):
        level = data.split("_")[1]
        session["level"] = level

        interface_lang = session.get("interface_lang", "en")
        prompt = STYLE_PROMPT.get(interface_lang, STYLE_PROMPT["en"])
        await query.message.reply_text(prompt, reply_markup=get_style_keyboard())

    # 🧲 Стиль общения
    elif data.startswith("style_"):
        chosen_style = data.split("_")[1]
        session["style"] = chosen_style
        interface_lang = session.get("interface_lang", "en")
        level = session.get("level", "A1")
        intro = get_intro_by_level_and_style(level, chosen_style, interface_lang)
        await query.message.reply_text(intro, reply_markup=get_mode_keyboard(session.get("mode", "text")))

    # 🔊 Переключение режимов
    elif data.startswith("mode_"):
        new_mode = data.split("_")[1]
        session["mode"] = new_mode

        interface_lang = session.get("interface_lang", "en")
        msg = MODE_SWITCH_MESSAGES.get(new_mode, {}).get(interface_lang, "Mode changed.")

        await query.message.edit_reply_markup(reply_markup=None)  # очистим старые кнопки
        await query.message.reply_text(msg, reply_markup=get_mode_keyboard(new_mode))
