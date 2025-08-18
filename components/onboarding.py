# components/onboarding.py
from __future__ import annotations
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from state.session import user_sessions
from components.promo import activate_promo
from components.profile_db import get_user_profile  # читаем как раньше
from components.safety import safe_save_user_profile  # <-- ИСПОЛЬЗУЕМ АДАПТЕР
from utils.decorators import safe_handler
from components.promo_texts import PROMO_ASK, PROMO_SUCCESS, PROMO_FAIL, PROMO_ALREADY_USED
from handlers.chat.prompt_templates import INTERFACE_LANG_PROMPT, TARGET_LANG_PROMPT
from components.language import get_target_language_keyboard, LANGUAGES
from components.levels import get_level_keyboard, LEVEL_PROMPT
from components.style import get_style_keyboard, STYLE_LABEL_PROMPT
from handlers.chat.levels_text import get_level_guide, LEVEL_GUIDE_BUTTON, LEVEL_GUIDE_CLOSE_BUTTON
from handlers.chat.prompt_templates import START_MESSAGE, MATT_INTRO, INTRO_QUESTIONS, INTRO_QUESTIONS_EASY

import random
import logging
import re

logger = logging.getLogger(__name__)

# --- локальные валидаторы/парсеры ---
_LANG_CODE_RE = re.compile(r"^(en|ru|fr|es|de|sv|fi)$")

def _parse_callback_value(data: str, expected_prefix: str) -> str | None:
    if not data or ":" not in data:
        return None
    prefix, value = data.split(":", 1)
    if prefix != expected_prefix:
        return None
    value = (value or "").strip()
    return value or None

def _is_lang_code(value: str) -> bool:
    return bool(value and _LANG_CODE_RE.match(value))

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
    return InlineKeyboardMarkup([[InlineKeyboardButton("🆗 OK", callback_data="onboarding_ok")]])

def get_level_guide_keyboard(lang):
    return InlineKeyboardMarkup([[InlineKeyboardButton(LEVEL_GUIDE_CLOSE_BUTTON.get(lang, LEVEL_GUIDE_CLOSE_BUTTON["en"]), callback_data="close_level_guide")]])

# --- ШАГ 1. /start — Выбор языка интерфейса ---
@safe_handler
async def send_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    session["onboarding_stage"] = "awaiting_language"

    # На первом шаге — русский по умолчанию (как было)
    lang = "ru"
    await context.bot.send_message(
        chat_id=chat_id,
        text=INTERFACE_LANG_PROMPT.get(lang, INTERFACE_LANG_PROMPT["en"]),
        reply_markup=get_interface_language_keyboard(),
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
    session["onboarding_stage"] = "awaiting_promo"

    # Сразу сохраним язык интерфейса в профиль
    try:
        safe_save_user_profile(chat_id, interface_lang=lang_code)
    except Exception:
        logger.exception("Failed to save interface_lang=%s for chat_id=%s", lang_code, chat_id)

    await query.edit_message_text(text=PROMO_ASK.get(lang_code, PROMO_ASK["en"]))

# --- ШАГ 3. Обработка промокода (или отказ) ---
@safe_handler
async def promo_code_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    lang_code = session.get("interface_lang", "en")
    promo_code = (update.message.text or "").strip()

    # Отказ от промокода
    if promo_code.lower() in ["нет", "no"]:
        session["promo_code_used"] = None
        session["promo_type"] = None
        await context.bot.send_message(
            chat_id=chat_id,
            text=START_MESSAGE.get(lang_code, START_MESSAGE["en"]),
            reply_markup=get_ok_keyboard(),
        )
        session["onboarding_stage"] = "awaiting_ok"
        return

    # Пытаемся активировать промо в session (он модифицируется на месте)
    success, reason = activate_promo(session, promo_code)
    if success:
        # Переносим значения из session в профиль и сохраняем ЧЕРЕЗ АДАПТЕР
        profile = get_user_profile(chat_id) or {"chat_id": chat_id}

        profile["promo_code_used"] = session.get("promo_code_used")
        profile["promo_type"] = session.get("promo_type")
        profile["promo_activated_at"] = session.get("promo_activated_at")
        profile["promo_days"] = session.get("promo_days")
        # Возможно присутствуют новые поля — передадим, адаптер отбросит, если схема старая:
        extra_minutes = session.get("promo_minutes")
        used_codes = session.get("promo_used_codes")

        safe_save_user_profile(
            chat_id,
            promo_code_used=profile.get("promo_code_used"),
            promo_type=profile.get("promo_type"),
            promo_activated_at=profile.get("promo_activated_at"),
            promo_days=profile.get("promo_days"),
            promo_minutes=extra_minutes,           # может отсутствовать — адаптер отбросит
            promo_used_codes=used_codes,           # список — адаптер отбросит, если не поддерживается
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=PROMO_SUCCESS.get(lang_code, PROMO_SUCCESS["en"]),
            reply_markup=get_ok_keyboard(),
        )
        session["onboarding_stage"] = "awaiting_ok"
    else:
        if reason == "invalid":
            await context.bot.send_message(chat_id=chat_id, text=PROMO_FAIL.get(lang_code, PROMO_FAIL["en"]))
        elif reason == "already_used":
            await context.bot.send_message(chat_id=chat_id, text=PROMO_ALREADY_USED.get(lang_code, PROMO_ALREADY_USED["en"]))
        # остаёмся на этом шаге
        session["onboarding_stage"] = "awaiting_promo"

# --- ШАГ 4. OK — выбор языка для изучения ---
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
        reply_markup=get_target_language_keyboard(session),
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

    try:
        safe_save_user_profile(chat_id, target_lang=lang_code)
    except Exception:
        logger.exception("Failed to save target_lang=%s for chat_id=%s", lang_code, chat_id)

    interface_lang = session.get("interface_lang", "ru")
    await query.edit_message_text(
        text=LEVEL_PROMPT.get(interface_lang, LEVEL_PROMPT["en"]),
        reply_markup=get_level_keyboard(interface_lang),
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
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(LEVEL_GUIDE_CLOSE_BUTTON.get(interface_lang, LEVEL_GUIDE_CLOSE_BUTTON["en"]), callback_data="close_level_guide")]]),
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
        reply_markup=get_level_keyboard(interface_lang),
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

    try:
        safe_save_user_profile(chat_id, level=level)
    except Exception:
        logger.exception("Failed to save level=%s for chat_id=%s", level, chat_id)

    interface_lang = session.get("interface_lang", "ru")
    await query.edit_message_text(
        text=STYLE_LABEL_PROMPT.get(interface_lang, STYLE_LABEL_PROMPT["en"]),
        reply_markup=get_style_keyboard(interface_lang),
    )

# --- ШАГ 7. Стиль — финал онбординга ---
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

    try:
        safe_save_user_profile(chat_id, style=style)
    except Exception:
        logger.exception("Failed to save style=%s for chat_id=%s", style, chat_id)

    interface_lang = session.get("interface_lang", "ru")
    await query.edit_message_text(text={"ru": "Отличный выбор 🌷", "en": "Great choice 🌷"}.get(interface_lang, "Great choice 🌷"))
    await onboarding_final(update, context)

# --- Приветствие Мэтта и первый вопрос ---
@safe_handler
async def onboarding_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import random
    chat_id = update.effective_chat.id if hasattr(update, "effective_chat") else update.callback_query.message.chat_id
    session = user_sessions.setdefault(chat_id, {})

    interface_lang = session.get("interface_lang", "en")
    level = session.get("level", "A2")
    target_lang = session.get("target_lang", session.get("interface_lang", "en"))

    # Вопросы — зависят от уровня
    if level in ("A0", "A1", "A2"):
        pool = INTRO_QUESTIONS_EASY.get(target_lang, INTRO_QUESTIONS_EASY.get("en", ["Hi! How are you today?"]))
    else:
        pool = INTRO_QUESTIONS.get(target_lang, INTRO_QUESTIONS.get("en", ["What’s up?"]))
    question = random.choice(pool)

    # 1) Приветствие + вопрос
    intro_text = MATT_INTRO.get(interface_lang, MATT_INTRO["en"])
    await context.bot.send_message(chat_id=chat_id, text=intro_text)
    await context.bot.send_message(chat_id=chat_id, text=question)

    # 2) Записываем обе реплики как ответы ассистента в историю
    history = session.setdefault("history", [])
    history.append({"role": "assistant", "content": intro_text})
    history.append({"role": "assistant", "content": question})

    session["onboarding_stage"] = "complete"
