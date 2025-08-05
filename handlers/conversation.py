from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from state.session import user_sessions

from components.language import get_target_language_keyboard, LANGUAGES, TARGET_LANG_PROMPT
from components.levels import get_level_keyboard, LEVEL_PROMPT
from components.style import get_style_keyboard, STYLE_LABEL_PROMPT

from handlers.chat.prompt_templates import (
    PREPARING_MESSAGE, START_MESSAGE, MATT_INTRO, INTRO_QUESTIONS
)

import random

def get_interface_language_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("Русский", callback_data="interface_lang:ru"),
            InlineKeyboardButton("English", callback_data="interface_lang:en"),
        ],
        # Добавь сюда больше языков, если потребуется
    ]
    return InlineKeyboardMarkup(keyboard)

def get_ok_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🆗 OK", callback_data="onboarding_ok")]])

# --- /start ---
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_sessions[chat_id] = {}
    await update.message.reply_text(
        PREPARING_MESSAGE.get("ru"),
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        "Выбери язык интерфейса / Choose interface language:",
        reply_markup=get_interface_language_keyboard()
    )

# --- Выбор языка интерфейса ---
async def interface_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang_code = query.data.split(":")[1]
    chat_id = query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})
    session["interface_lang"] = lang_code
    session["onboarding_stage"] = "awaiting_ok"
    await query.edit_message_text(
        text=START_MESSAGE.get(lang_code, START_MESSAGE["en"]),
        reply_markup=get_ok_keyboard()
    )

# --- OK-кнопка ---
async def onboarding_ok_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("onboarding_ok_callback вызван!")
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})
    lang_code = session.get("interface_lang", "ru")
    await query.edit_message_text(
        text=TARGET_LANG_PROMPT.get(lang_code, TARGET_LANG_PROMPT["en"]),
        reply_markup=get_target_language_keyboard()
    )

# --- Выбор языка для изучения ---
async def target_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang_code = query.data.split(":")[1]
    chat_id = query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})
    session["target_lang"] = lang_code
    session["onboarding_stage"] = "awaiting_level"
    interface_lang = session.get("interface_lang", "ru")
    await query.edit_message_text(
        text=LEVEL_PROMPT.get(interface_lang, LEVEL_PROMPT["en"]),
        reply_markup=get_level_keyboard(interface_lang)
    )

# --- Выбор уровня ---
async def level_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    level = query.data.split(":")[1]
    chat_id = query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})
    session["level"] = level
    session["onboarding_stage"] = "awaiting_style"
    interface_lang = session.get("interface_lang", "ru")
    await query.edit_message_text(
        text=STYLE_LABEL_PROMPT.get(interface_lang, STYLE_LABEL_PROMPT["en"]),
        reply_markup=get_style_keyboard(interface_lang)
    )

# --- Выбор стиля общения ---
async def style_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    style = query.data.split(":")[1]
    chat_id = query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})
    session["style"] = style
    session["onboarding_stage"] = "complete"
    # Просто убираем кнопки (редактируем сообщение, оставляя его пустым)
    await query.edit_message_text(text=" ")
    # Сразу отправляем приветствие от Мэтта и первый вопрос
    await onboarding_final(update, context)


# --- Финальное приветствие и вовлекающий вопрос ---
async def onboarding_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id if hasattr(update, "effective_chat") else update.callback_query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})
    interface_lang = session.get("interface_lang", "en")
    target_lang = session.get("target_lang", interface_lang)

    await context.bot.send_message(
        chat_id=chat_id,
        text=MATT_INTRO.get(interface_lang, MATT_INTRO["en"])
    )
    question = random.choice(INTRO_QUESTIONS.get(target_lang, INTRO_QUESTIONS["en"]))
    await context.bot.send_message(chat_id=chat_id, text=question)

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
    elif data.startswith("style:"):
        await style_callback(update, context)
    # Можно добавить дополнительные этапы, если потребуется!
