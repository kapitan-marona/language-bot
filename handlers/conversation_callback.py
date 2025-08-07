from telegram import Update
from telegram.ext import ContextTypes
from handlers.onboarding import (
    interface_language_callback,
    onboarding_ok_callback,
    target_language_callback,
    level_callback,
    level_guide_callback,
    close_level_guide_callback,
    style_callback,
)
from handlers.mode import get_mode_keyboard
from state.session import user_sessions

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("interface_lang:"):
        await interface_language_callback(update, context)
    elif data == "onboarding_ok":
        await onboarding_ok_callback(update, context)
    elif data.startswith("target_lang:"):
        await target_language_callback(update, context)
    elif data.startswith("level:"):
        await level_callback(update, context)
    elif data == "level_guide":
        await level_guide_callback(update, context)
    elif data == "close_level_guide":
        await close_level_guide_callback(update, context)
    elif data.startswith("style:"):
        await style_callback(update, context)
    elif data == "mode:voice":
        chat_id = query.message.chat_id
        session = user_sessions.setdefault(chat_id, {})
        session["mode"] = "voice"
        interface_lang = session.get("interface_lang", "ru")
        await query.edit_message_text(
            text="🔊 Теперь отвечаю голосом" if interface_lang == "ru" else "🔊 Now I'll reply with voice",
            reply_markup=get_mode_keyboard("voice", interface_lang)
        )
    elif data == "mode:text":
        chat_id = query.message.chat_id
        session = user_sessions.setdefault(chat_id, {})
        session["mode"] = "text"
        interface_lang = session.get("interface_lang", "ru")
        await query.edit_message_text(
            text="⌨️ Теперь отвечаю текстом" if interface_lang == "ru" else "⌨️ Now I'll reply with text",
            reply_markup=get_mode_keyboard("text", interface_lang)
        )

