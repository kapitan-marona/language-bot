from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from state.session import user_sessions
from components.promo import activate_promo
from components.profile_db import get_user_profile, save_user_profile  # <-- добавлено
from utils.decorators import safe_handler
from components.promo_texts import PROMO_ASK, PROMO_SUCCESS, PROMO_FAIL, PROMO_ALREADY_USED
from handlers.chat.prompt_templates import INTERFACE_LANG_PROMPT, TARGET_LANG_PROMPT
from components.language import get_target_language_keyboard, LANGUAGES
from components.levels import get_level_keyboard, LEVEL_PROMPT
from components.style import get_style_keyboard, STYLE_LABEL_PROMPT
from handlers.chat.levels_text import get_level_guide, LEVEL_GUIDE_BUTTON, LEVEL_GUIDE_CLOSE_BUTTON
from handlers.chat.prompt_templates import START_MESSAGE, MATT_INTRO, INTRO_QUESTIONS

import random
import logging
import re

logger = logging.getLogger(__name__)

# --- локальные валидаторы/парсеры ---
_LANG_CODE_RE = re.compile(r"^(en|ru|fr|es|de|sv|fi)$")

def _parse_callback_value(data: str, expected_prefix: str) -> str | None:
    """Безопасно достаёт значение из callback_data формата '<prefix>:<value>'."""
    if not data or ":" not in data:
        return None
    prefix, value = data.split(":", 1)
    if prefix != expected_prefix:
        return None
    value = (value or "").strip()
    return value or None

def _is_lang_code(value: str) -> bool:
    return bool(value and _LANG_CODE_RE.match(value))

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
@safe_handler
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
@safe_handler
async def interface_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    raw = query.data
    lang_code = _parse_callback_value(raw, "interface_lang")
    if not _is_lang_code(lang_code or ""):
        logger.warning("Invalid interface_lang callback_data=%r, fallback to 'en'", raw)
        lang_code = "en"

    chat_id = query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})
    session["interface_lang"] = lang_code
    context.user_data['ui_lang'] = lang_code
    session["onboarding_stage"] = "awaiting_promo"

    # Не передаём ReplyKeyboardRemove в edit_message_text: Telegram ожидает inline-клавиатуру
    await query.edit_message_text(text=(
        "У тебя есть промокод?\n👉 Отправь его командой: /promo <код>\n\nНажми 🆗, чтобы продолжить без промокода"
        if lang_code == 'ru' else
        "Do you have a promo code?\n👉 Send it with the command: /promo <code>\n\nTap 🆗 to continue without a promo code"
    ), reply_markup=get_ok_keyboard())

# --- ШАГ 3. Обработка промокода от пользователя (или отказ) ---
@safe_handler
async def promo_code_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    lang_code = session.get("interface_lang", "en")
    promo_input = (update.message.text or "").strip()

    # Пользователь может отказаться вводить промокод
    if promo_input.lower() in ["нет", "no"]:
        await context.bot.send_message(
            chat_id=chat_id,
            text=START_MESSAGE.get(lang_code, START_MESSAGE["en"]),
            reply_markup=get_ok_keyboard()
        )
        session["onboarding_stage"] = "awaiting_ok"
        return

    # На этапе онбординга принимаем промокоды ТОЛЬКО через команду /promo <код>
    tip = ("Введите промокод командой: /promo <код>" if lang_code == "ru"
           else "Send the promo code using the command: /promo <code>")
    await context.bot.send_message(chat_id=chat_id, text=tip)
    # Остаёмся на этапе ввода промокода — ждём /promo или 'нет'
    session["onboarding_stage"] = "awaiting_promo"
    return
# --- ШАГ 4. OK — Выбор языка для изучения ---
@safe_handler
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
@safe_handler
async def target_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    raw = query.data
    lang_code = _parse_callback_value(raw, "target_lang")
    if not _is_lang_code(lang_code or ""):
        logger.warning("Invalid target_lang callback_data=%r, fallback to 'en'", raw)
        lang_code = "en"

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
@safe_handler
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
@safe_handler
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
@safe_handler
async def level_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    raw = query.data
    level = _parse_callback_value(raw, "level")
    if not level:
        logger.warning("Invalid level callback_data=%r, fallback to 'A2'", raw)
        level = "A2"

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
@safe_handler
async def style_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    raw = query.data
    style = _parse_callback_value(raw, "style")
    if not style:
        logger.warning("Invalid style callback_data=%r, fallback to 'casual'", raw)
        style = "casual"

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
@safe_handler
async def onboarding_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id if hasattr(update, "effective_chat") else update.callback_query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})

    interface_lang = session.get("interface_lang", "en")
    target_lang = session.get("target_lang", interface_lang)

    # 1) Текст приветствия и вопрос
    intro_text = MATT_INTRO.get(interface_lang, MATT_INTRO["en"])
    question = random.choice(INTRO_QUESTIONS.get(target_lang, INTRO_QUESTIONS["en"]))

    # 2) Отправляем пользователю
    await context.bot.send_message(chat_id=chat_id, text=intro_text)
    await context.bot.send_message(chat_id=chat_id, text=question)

    # 3) ВАЖНО: записываем обе реплики в историю как ответы ассистента
    history = session.setdefault("history", [])
    history.append({"role": "assistant", "content": intro_text})
    history.append({"role": "assistant", "content": question})

    # (по желанию) можно отметить, что онбординг завершён
    session["onboarding_stage"] = "complete"
