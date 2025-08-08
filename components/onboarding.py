from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from state.session import user_sessions
from components.promo import activate_promo
from components.promo_texts import PROMO_ASK, PROMO_SUCCESS, PROMO_FAIL, PROMO_ALREADY_USED
from handlers.chat.prompt_templates import INTERFACE_LANG_PROMPT, TARGET_LANG_PROMPT
from components.language import get_target_language_keyboard, LANGUAGES
from components.levels import get_level_keyboard, LEVEL_PROMPT
from components.style import get_style_keyboard, STYLE_LABEL_PROMPT
from handlers.chat.levels_text import get_level_guide, LEVEL_GUIDE_BUTTON, LEVEL_GUIDE_CLOSE_BUTTON
from handlers.chat.prompt_templates import START_MESSAGE, MATT_INTRO, INTRO_QUESTIONS

import random

# Локализованное сообщение после выбора стиля
STYLE_SELECTED_MSG = {
    "ru": "Отличный выбор 🌷",
    "en": "Great choice 🌷"
}

def get_interface_language_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Русский", callback_data="interface_lang:ru"),
            InlineKeyboardButton("English", callback_data="interface_lang:en"),
        ]
    ])

def get_ok_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🆗 OK", callback_data="onboarding_ok")]
    ])

def get_level_guide_keyboard(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(LEVEL_GUIDE_CLOSE_BUTTON.get(lang, LEVEL_GUIDE_CLOSE_BUTTON["en"]), callback_data="close_level_guide")]
    ])

# --- ШАГ 1. /start — Выбор языка интерфейса ---
async def send_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    session["onboarding_stage"] = "awaiting_language"

    # На первом шаге по умолчанию язык интерфейса русский
    lang = 'ru'
    await context.bot.send_message(
        chat_id=chat_id,
        text=INTERFACE_LANG_PROMPT.get(lang, INTERFACE_LANG_PROMPT['en']),
        reply_markup=get_interface_language_keyboard()
    )

# --- ШАГ 2. Выбран язык — спрашиваем промокод ---
async def interface_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang_code = query.data.split(":")[1]
    chat_id = query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})
    session["interface_lang"] = lang_code
    session["onboarding_stage"] = "awaiting_promo"
    await query.edit_message_text(
        text=PROMO_ASK.get(lang_code, PROMO_ASK["en"]),
        reply_markup=ReplyKeyboardRemove()
    )

# --- ШАГ 3. Обработка промокода от пользователя (или отказ) ---
async def promo_code_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    lang_code = session.get("interface_lang", "en")
    promo_code = (update.message.text or "").strip()

    # Пользователь может отказаться вводить промокод
    if promo_code.lower() in ["нет", "no"]:
        session["promo_code_used"] = None
        session["promo_type"] = None
        await context.bot.send_message(
            chat_id=chat_id,
            text=START_MESSAGE.get(lang_code, START_MESSAGE["en"]),
            reply_markup=get_ok_keyboard()
        )
        session["onboarding_stage"] = "awaiting_ok"
        return

    # Активируем промокод
    success, reason = activate_promo(session, promo_code)
    if success:
        await context.bot.send_message(
            chat_id=chat_id,
            text=PROMO_SUCCESS.get(lang_code, PROMO_SUCCESS["en"]),
            reply_markup=get_ok_keyboard()
        )
        session["onboarding_stage"] = "awaiting_ok"
    else:
        if reason == "invalid":
            await context.bot.send_message(
                chat_id=chat_id,
                text=PROMO_FAIL.get(lang_code, PROMO_FAIL["en"]),
            )
        elif reason == "already_used":
            await context.bot.send_message(
                chat_id=chat_id,
                text=PROMO_ALREADY_USED.get(lang_code, PROMO_ALREADY_USED["en"]),
            )
        # Остаёмся на этапе ввода промокода — ждём новый ввод или "нет"
        session["onboarding_stage"] = "awaiting_promo"

# --- ШАГ 4. OK — Выбор языка для изучения ---
async def onboarding_ok_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})
    lang_code = session.get("interface_lang", "ru")
    session["onboarding_stage"] = "awaiting_target_lang"
    await query.edit_message_text(
        text=TARGET_LANG_PROMPT.get(lang_code, TARGET_LANG_PROMPT["en"]),
        reply_markup=get_target_language_keyboard(session)  # Учитывает промокоды (например, только EN)
    )

# --- ШАГ 5. Выбор языка для изучения — выбор уровня ---
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

# --- Гайд по уровням ---
async def level_guide_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})
    interface_lang = session.get("interface_lang", "ru")
    await query.edit_message_text(
        text=get_level_guide(interface_lang),
        parse_mode="Markdown",
        reply_markup=get_level_guide_keyboard(interface_lang)
    )

# --- Закрыть гайд по уровням ---
async def close_level_guide_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})
    interface_lang = session.get("interface_lang", "ru")
    await query.edit_message_text(
        text=LEVEL_PROMPT.get(interface_lang, LEVEL_PROMPT["en"]),
        reply_markup=get_level_keyboard(interface_lang)
    )

# --- ШАГ 6. Выбор уровня — стиль общения ---
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

# --- ШАГ 7. Выбор стиля — приветствие и вовлекающий вопрос ---
async def style_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    style = query.data.split(":")[1]
    chat_id = query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})
    session["style"] = style
    session["onboarding_stage"] = "complete"
    interface_lang = session.get("interface_lang", "ru")
    await query.edit_message_text(
        text=STYLE_SELECTED_MSG.get(interface_lang, STYLE_SELECTED_MSG["en"])
    )
    await onboarding_final(update, context)

# --- Приветствие Мэтта и первый вопрос ---
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
