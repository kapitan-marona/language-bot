from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from state.session import user_sessions

# Импорт всех текстов из prompt_templates или texts.py
from handlers.chat.prompt_templates import (
    START_MESSAGE, MATT_INTRO, INTRO_QUESTIONS, ONBOARDING_MESSAGE
)

import random

# Список поддерживаемых языков (и для интерфейса, и для изучения)
SUPPORTED_LANGUAGES = [
    ("🇷🇺 Русский", "ru"),
    ("🇬🇧 English", "en"),
    ("🇫🇷 Français", "fr"),
    ("🇪🇸 Español", "es"),
    ("🇩🇪 Deutsch", "de"),
    ("🇸🇪 Svenska", "sv"),
    ("🇫🇮 Suomi", "fi"),
]

def get_interface_language_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"interface_lang:{code}")]
        for name, code in SUPPORTED_LANGUAGES
    ]
    return InlineKeyboardMarkup(keyboard)

def get_target_language_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"target_lang:{code}")]
        for name, code in SUPPORTED_LANGUAGES
    ]
    return InlineKeyboardMarkup(keyboard)

PREPARING_MESSAGE = {
    "ru": "⌨️ Подготовка…",
    "en": "⌨️ Preparing…"
}

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # Сброс всей сессии пользователя
    user_sessions[chat_id] = {}
    # Определяем язык по умолчанию
    interface_lang = context.user_data.get("interface_lang", "ru")
    await update.message.reply_text(
        PREPARING_MESSAGE.get(interface_lang, PREPARING_MESSAGE["en"]),
        reply_markup=ReplyKeyboardRemove()
    )
    # Приветствие и выбор языка
    await update.message.reply_text(
        ONBOARDING_MESSAGE,
        reply_markup=get_interface_language_keyboard()
    )

async def interface_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang_code = query.data.split(":")[1]
    chat_id = query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})
    session["interface_lang"] = lang_code
    session["onboarding_stage"] = "awaiting_target_lang"
    # Показываем выбор языка для изучения
    await query.edit_message_text(
        text="🌍 Выбери язык для изучения:" if lang_code == "ru" else "🌍 Choose a language to learn:",
        reply_markup=get_target_language_keyboard()
    )

# После выбора target_lang вызывается следующее
async def target_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang_code = query.data.split(":")[1]
    chat_id = query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})
    session["target_lang"] = lang_code
    session["onboarding_stage"] = "awaiting_level"
    # Показываем выбор уровня (ты можешь импортировать get_level_keyboard)
    from components.levels import get_level_keyboard
    await query.edit_message_text(
        text="Выбери свой уровень:" if session["interface_lang"] == "ru" else "Choose your level:",
        reply_markup=get_level_keyboard(session["interface_lang"])
    )

# Дальше стиль общения, далее финальный онбординг
async def onboarding_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    interface_lang = session.get("interface_lang", "en")
    target_lang = session.get("target_lang", interface_lang)
    await context.bot.send_message(
        chat_id=chat_id,
        text=MATT_INTRO.get(interface_lang, MATT_INTRO["en"])
    )
    question = random.choice(INTRO_QUESTIONS.get(target_lang, INTRO_QUESTIONS["en"]))
    await context.bot.send_message(chat_id=chat_id, text=question)
