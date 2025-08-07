from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from state.session import user_sessions
from components.language import get_target_language_keyboard, LANGUAGES, TARGET_LANG_PROMPT
from components.levels import get_level_keyboard, LEVEL_PROMPT
from components.style import get_style_keyboard, STYLES, STYLE_LABEL_PROMPT
from handlers.chat.levels_text import get_level_guide, LEVEL_GUIDE_BUTTON, LEVEL_GUIDE_CLOSE_BUTTON
from handlers.chat.prompt_templates import START_MESSAGE, MATT_INTRO, INTRO_QUESTIONS

import random

def get_interface_language_keyboard():
    keyboard = [
        [InlineKeyboardButton("Русский", callback_data="interface_lang:ru"),
         InlineKeyboardButton("English", callback_data="interface_lang:en")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_ok_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🆗 OK", callback_data="onboarding_ok")]])

def get_target_language_keyboard():
    """
    Возвращает InlineKeyboardMarkup с поддерживаемыми языками (по 2 в ряд).
    """
    buttons = []
    row = []
    for code, label in LANGUAGES.items():
        row.append(InlineKeyboardButton(label, callback_data=f"target_lang:{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

def get_level_keyboard(lang_code="en"):
    """
    Возвращает InlineKeyboardMarkup для выбора уровня и кнопки-справки.
    """
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton

    levels_row1 = [
        InlineKeyboardButton("A0", callback_data="level:A0"),
        InlineKeyboardButton("A1", callback_data="level:A1"),
        InlineKeyboardButton("A2", callback_data="level:A2"),
    ]
    levels_row2 = [
        InlineKeyboardButton("B1", callback_data="level:B1"),
        InlineKeyboardButton("B2", callback_data="level:B2"),
        InlineKeyboardButton("C1", callback_data="level:C1"),
        InlineKeyboardButton("C2", callback_data="level:C2"),
    ]
    levels_guide_row = [
        InlineKeyboardButton(
            LEVEL_GUIDE_BUTTON.get(lang_code, LEVEL_GUIDE_BUTTON["en"]),
            callback_data="level_guide"
        )
    ]
    return InlineKeyboardMarkup([levels_row1, levels_row2, levels_guide_row])


def get_level_guide_keyboard(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(LEVEL_GUIDE_CLOSE_BUTTON.get(lang, LEVEL_GUIDE_CLOSE_BUTTON["en"]), callback_data="close_level_guide")]
    ])


def get_style_keyboard(lang_code):
    styles_row = [
        InlineKeyboardButton(STYLES["casual"][lang_code], callback_data="style:casual"),
        InlineKeyboardButton(STYLES["formal"][lang_code], callback_data="style:formal")
    ]
    return InlineKeyboardMarkup([styles_row])

# === ОБРАБОТЧИКИ ===

async def send_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})

    # Если админ в спец-режиме — напомнить о /user
    if session.get("is_admin", False) and session.get("onboarding_stage") == "admin":
        await context.bot.send_message(
            chat_id=chat_id,
            text="👑 Ты в админ-режиме! Чтобы вернуться к обычному боту, напиши /user."
        )
        return

    # Обычный онбординг
    session["onboarding_stage"] = "awaiting_language"
    await context.bot.send_message(
        chat_id=chat_id,
        text=START_MESSAGE.get(session.get("interface_lang", "ru"), START_MESSAGE['en'])
    )
    await context.bot.send_message(
        chat_id=chat_id,
        text="Выбери язык интерфейса / Choose interface language:",
        reply_markup=get_interface_language_keyboard()
    )


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

async def onboarding_ok_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})
    lang_code = session.get("interface_lang", "ru")
    await query.edit_message_text(
        text=TARGET_LANG_PROMPT.get(lang_code, TARGET_LANG_PROMPT["en"]),
        reply_markup=get_target_language_keyboard()
    )

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

async def style_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    style = query.data.split(":")[1]
    chat_id = query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})
    session["style"] = style
    session["onboarding_stage"] = "complete"
    await query.edit_message_text(text=" Отличный выбор 🌷 ")
    await onboarding_final(update, context)

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



