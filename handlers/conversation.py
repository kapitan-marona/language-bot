from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from config.config import ADMINS
from state.session import user_sessions

from components.language import get_target_language_keyboard, LANGUAGES, TARGET_LANG_PROMPT

from handlers.chat.prompt_templates import (
    PREPARING_MESSAGE, START_MESSAGE, MATT_INTRO, INTRO_QUESTIONS
)
from components.style import get_style_keyboard, STYLE_LABEL_PROMPT

from components.levels import get_level_keyboard, LEVEL_PROMPT

from handlers.chat.levels_text import get_level_guide, LEVEL_GUIDE_BUTTON, LEVEL_GUIDE_CLOSE_BUTTON

from components.mode import get_mode_keyboard

import random
import sys
import os

# --- Обработчик callback'ов ---
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    print(f"callback data: {update.callback_query.data}")
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



