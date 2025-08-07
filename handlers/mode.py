from telegram import Update
from telegram.ext import ContextTypes
from state.session import user_sessions
from components.mode import get_mode_keyboard, MODE_SWITCH_MESSAGES

async def handle_mode_switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})
    interface_lang = session.get("interface_lang", "ru")

    if query.data == "mode:voice":
        session["mode"] = "voice"
        await query.edit_message_text(
            text=MODE_SWITCH_MESSAGES["voice"].get(interface_lang, MODE_SWITCH_MESSAGES["voice"]["en"]),
            reply_markup=get_mode_keyboard("voice", interface_lang)
        )
    elif query.data == "mode:text":
        session["mode"] = "text"
        await query.edit_message_text(
            text=MODE_SWITCH_MESSAGES["text"].get(interface_lang, MODE_SWITCH_MESSAGES["text"]["en"]),
            reply_markup=get_mode_keyboard("text", interface_lang)
        )
