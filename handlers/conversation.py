from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from state.session import user_sessions
from handlers.chat.prompt_templates import START_MESSAGE, MATT_INTRO, INTRO_QUESTIONS

from components.levels import get_level_keyboard, LEVEL_PROMPT
from components.language import get_target_language_keyboard, TARGET_LANG_PROMPT
from components.style import get_style_keyboard, STYLE_LABEL_PROMPT

import random

# Клавиатуры для языков, уровней, стиля
def get_interface_language_keyboard():
    langs = [
        [InlineKeyboardButton("Русский", callback_data="lang:ru"), InlineKeyboardButton("English", callback_data="lang:en")]
    ]
    return InlineKeyboardMarkup(langs)

def get_target_language_keyboard():
    langs = [
        [InlineKeyboardButton("English", callback_data="target:en"),
         InlineKeyboardButton("Español", callback_data="target:es"),
         InlineKeyboardButton("Français", callback_data="target:fr")],
        [InlineKeyboardButton("Deutsch", callback_data="target:de"),
         InlineKeyboardButton("Svenska", callback_data="target:sv"),
         InlineKeyboardButton("Suomi", callback_data="target:fi")],
        [InlineKeyboardButton("Русский", callback_data="target:ru")]
    ]
    return InlineKeyboardMarkup(langs)

def get_level_keyboard():
    levels = [
        [InlineKeyboardButton("A1", callback_data="level:A1"),
         InlineKeyboardButton("A2", callback_data="level:A2"),
         InlineKeyboardButton("B1", callback_data="level:B1"),
         InlineKeyboardButton("B2", callback_data="level:B2")],
        [InlineKeyboardButton("C1", callback_data="level:C1"),
         InlineKeyboardButton("C2", callback_data="level:C2")]
    ]
    return InlineKeyboardMarkup(levels)

def get_style_keyboard():
    styles = [
        [InlineKeyboardButton("Casual", callback_data="style:casual")]
    ]
    return InlineKeyboardMarkup(styles)

# Запуск онбординга: /start
async def start_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    session.clear()  # Чистим старую сессию, если была
    await context.bot.send_message(
        chat_id=chat_id,
        text="Выбери язык интерфейса / Choose interface language:",
        reply_markup=get_interface_language_keyboard()
    )

# Обработка нажатий на кнопки
async def conversation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data
    session = user_sessions.setdefault(ch_
