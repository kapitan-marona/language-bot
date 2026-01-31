from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from state.session import user_sessions
from components.promo import activate_promo
from components.profile_db import get_user_profile, save_user_profile
from utils.decorators import safe_handler
from components.promo_texts import PROMO_ASK, PROMO_SUCCESS, PROMO_FAIL, PROMO_ALREADY_USED
from handlers.chat.prompt_templates import INTERFACE_LANG_PROMPT, TARGET_LANG_PROMPT
from components.language import get_target_language_keyboard, LANGUAGES
from components.levels import get_level_keyboard, LEVEL_PROMPT
from components.style import get_style_keyboard, STYLE_LABEL_PROMPT
from handlers.chat.levels_text import get_level_guide, LEVEL_GUIDE_BUTTON, LEVEL_GUIDE_CLOSE_BUTTON
from handlers.chat.prompt_templates import START_MESSAGE, MATT_INTRO
from handlers.chat.prompt_templates import pick_intro_question
from components.access import enforce_and_set_active_language, ensure_access_defaults


# 🔽 Новое: берём id стикера напрямую из конфига, без импорта из chat_handler
from components.stickers import STICKERS_CONFIG

import logging
import re
import random  # для вероятности отправки привет-стикера
import json

logger = logging.getLogger(__name__)

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
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🆗 OK", callback_data="onboarding_ok")]
    ])

def get_level_guide_keyboard(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(LEVEL_GUIDE_CLOSE_BUTTON.get(lang, LEVEL_GUIDE_CLOSE_BUTTON["en"]), callback_data="close_level_guide")]
    ])

def _append_tr_question_text(ui: str) -> str:
    if ui == "ru":
        return "Хочешь, я буду дублировать свои сообщения на русском языке?"
    return "Do you want me to also show my replies in English?"

def get_append_tr_keyboard(ui: str) -> InlineKeyboardMarkup:
    yes = "Да" if ui == "ru" else "Yes"
    no = "Нет" if ui == "ru" else "No"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(yes, callback_data="append_tr:yes"),
        InlineKeyboardButton(no,  callback_data="append_tr:no"),
    ]])

# --- локальная безопасная отправка привет-стикера (без зависимости от chat_handler) ---
async def maybe_send_sticker_hello(context: ContextTypes.DEFAULT_TYPE, chat_id: int, chance: float = 0.7):
    """
    Пытается отправить привет-стикер из пакета (ключ 'hello') с заданной вероятностью.
    Ошибки проглатывает тихо.
    """
    try:
        cfg = STICKERS_CONFIG.get("hello") or {}
        file_id = cfg.get("id")
        if not file_id:
            return
        if random.random() <= float(chance):
            await context.bot.send_sticker(chat_id=chat_id, sticker=file_id)
    except Exception:
        logger.debug("onboarding hello sticker failed", exc_info=True)

# --- ШАГ 1. /start — Выбор языка интерфейса ---
@safe_handler
async def send_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    session["onboarding_stage"] = "awaiting_language"
    session.setdefault("append_translation", False)  # дефолт
    lang = 'ru'
    await context.bot.send_message(
        chat_id=chat_id,
        text=INTERFACE_LANG_PROMPT.get(lang, INTERFACE_LANG_PROMPT['en']),
        reply_markup=get_interface_language_keyboard()
    )
    # 🔽 Было: maybe_send_sticker(...). Теперь — локально.
    await maybe_send_sticker_hello(context, chat_id, chance=0.7)

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

    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    session["interface_lang"] = lang_code
    session["onboarding_stage"] = "awaiting_promo"

    try:
        save_user_profile(chat_id, interface_lang=lang_code)
    except Exception:
        logger.exception("Failed to save interface_lang=%s for chat_id=%s", lang_code, chat_id)

    await query.edit_message_text(text=PROMO_ASK.get(lang_code, PROMO_ASK["en"]))

# --- ШАГ 3. Обработка промокода ---
@safe_handler
async def promo_code_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    lang_code = session.get("interface_lang", "en")
    promo_code = (update.message.text or "").strip().lower()

    if promo_code in ["нет", "no", "не", "nope", "nah", "неа", "нету"]:
        session["promo_code_used"] = None
        session["promo_type"] = None
        await context.bot.send_message(
            chat_id=chat_id,
            text=START_MESSAGE.get(lang_code, START_MESSAGE["en"]),
            reply_markup=get_ok_keyboard()
        )
        session["onboarding_stage"] = "awaiting_ok"
        return

    success, reason = activate_promo(session, promo_code)
    if success:
        profile = get_user_profile(chat_id) or {"chat_id": chat_id}
        profile["promo_code_used"] = session.get("promo_code_used")
        profile["promo_type"] = session.get("promo_type")
        profile["promo_activated_at"] = session.get("promo_activated_at")
        profile["promo_days"] = session.get("promo_days")
        save_user_profile(
            chat_id,
            promo_code_used=profile.get("promo_code_used"),
            promo_type=profile.get("promo_type"),
            promo_activated_at=profile.get("promo_activated_at"),
            promo_days=profile.get("promo_days"),
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=PROMO_SUCCESS.get(lang_code, PROMO_SUCCESS["en"]),
            reply_markup=get_ok_keyboard()
        )
        session["onboarding_stage"] = "awaiting_ok"
    else:
        if reason == "invalid":
            await context.bot.send_message(chat_id=chat_id, text=PROMO_FAIL.get(lang_code, PROMO_FAIL["en"]))
            session["onboarding_stage"] = "awaiting_promo"
        elif reason == "already_used":
            await context.bot.send_message(chat_id=chat_id, text=PROMO_ALREADY_USED.get(lang_code, PROMO_ALREADY_USED["en"]))
            await context.bot.send_message(
                chat_id=chat_id,
                text=START_MESSAGE.get(lang_code, START_MESSAGE["en"]),
                reply_markup=get_ok_keyboard()
            )
            session["onboarding_stage"] = "awaiting_ok"
        else:
            session["onboarding_stage"] = "awaiting_promo"

# --- ШАГ 4. OK — Выбор языка для изучения ---
@safe_handler
async def onboarding_ok_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    lang_code = session.get("interface_lang", "ru")
    session["onboarding_stage"] = "awaiting_target_lang"
    await query.edit_message_text(
        text=TARGET_LANG_PROMPT.get(lang_code, TARGET_LANG_PROMPT["en"]),
        reply_markup=get_target_language_keyboard(session)
    )

# --- ШАГ 5. Выбор языка — выбор уровня ---
@safe_handler
async def target_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    raw = query.data
    lang_code = _parse_callback_value(raw, "target_lang")
    if not _is_lang_code(lang_code or ""):
        logger.warning("Invalid target_lang callback_data=%r, fallback to 'en'", raw)
        lang_code = "en"

    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    session["target_lang"] = lang_code
    session["onboarding_stage"] = "awaiting_level"
    
        # NEW: enforce access rules (english_only, slots) + store active langs
    prof = get_user_profile(chat_id) or {"chat_id": chat_id}
    ensure_access_defaults(prof)
    ok, reason, active = enforce_and_set_active_language(prof, lang_code)
    if not ok:
        interface_lang = session.get("interface_lang", "ru")
        msg = "⛔️ Доступно только English по вашему промокоду." if (interface_lang == "ru" and reason == "english_only") else (
            "⛔️ Only English is available with your promo." if reason == "english_only" else (
                "⛔️ Нельзя выбрать этот язык сейчас." if interface_lang == "ru" else "⛔️ This language is not available right now."
            )
        )
        await query.edit_message_text(text=msg)
        return

    try:
        save_user_profile(chat_id, target_lang=lang_code, access_active_langs_json=json.dumps(active, ensure_ascii=False))
    except Exception:
        logger.exception("Failed to save target_lang=%s for chat_id=%s", lang_code, chat_id)

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
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    interface_lang = session.get("interface_lang", "ru")
    await query.edit_message_text(
        text=get_level_guide(interface_lang),
        parse_mode="Markdown",
        reply_markup=get_level_guide_keyboard(interface_lang)
    )

# --- Закрыть гайд ---
@safe_handler
async def close_level_guide_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    interface_lang = session.get("interface_lang", "ru")

    # После закрытия гайда показываем снова выбор уровня
    await query.edit_message_text(
        text=LEVEL_PROMPT.get(interface_lang, LEVEL_PROMPT["en"]),
        reply_markup=get_level_keyboard(interface_lang)
    )

# --- ШАГ 6. Выбор уровня — A0–A1: спросить про дублирование; иначе — стиль ---
@safe_handler
async def level_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    raw = query.data
    level = _parse_callback_value(raw, "level")
    if not level:
        logger.warning("Invalid level callback_data=%r, fallback to 'A2'", raw)
        level = "A2"

    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    session["level"] = level

    try:
        save_user_profile(chat_id, level=level)
    except Exception:
        logger.exception("Failed to save level=%s for chat_id=%s", level, chat_id)

    interface_lang = session.get("interface_lang", "ru")

    if level in ("A0", "A1"):
        session["onboarding_stage"] = "awaiting_append_tr"
        await query.edit_message_text(
            text=_append_tr_question_text(interface_lang),
            reply_markup=get_append_tr_keyboard(interface_lang)
        )
        return

    # для A2+ сразу стиль
    session["onboarding_stage"] = "awaiting_style"
    await query.edit_message_text(
        text=STYLE_LABEL_PROMPT.get(interface_lang, STYLE_LABEL_PROMPT["en"]),
        reply_markup=get_style_keyboard(interface_lang)
    )

# --- ШАГ 6b. Обработчик кнопок 'append_tr:yes|no' ---
@safe_handler
async def append_tr_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data or ""
    choice_yes = data.endswith(":yes")
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})

    session["append_translation"] = bool(choice_yes)

    # После выбора — переходим к стилю
    session["onboarding_stage"] = "awaiting_style"
    ui = session.get("interface_lang", "ru")
    await q.edit_message_text(
        text=STYLE_LABEL_PROMPT.get(ui, STYLE_LABEL_PROMPT["en"]),
        reply_markup=get_style_keyboard(ui)
    )

# --- ШАГ 7. Выбор стиля — завершение ---
@safe_handler
async def style_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    raw = query.data
    style = _parse_callback_value(raw, "style")
    if not style:
        logger.warning("Invalid style callback_data=%r, fallback to 'casual'", raw)
        style = "casual"

    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    session["style"] = style
    session["onboarding_stage"] = "complete"

    try:
        save_user_profile(chat_id, style=style)
    except Exception:
        logger.exception("Failed to save style=%s for chat_id=%s", style, chat_id)

    interface_lang = session.get("interface_lang", "ru")
    await query.edit_message_text(text=STYLE_SELECTED_MSG.get(interface_lang, STYLE_SELECTED_MSG["en"]))
    await onboarding_final(update, context)

# --- Финал: приветствие Мэтта и первый вопрос ---
@safe_handler
async def onboarding_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})

    interface_lang = session.get("interface_lang", "en")
    target_lang = session.get("target_lang", interface_lang)
    level = session.get("level", "A2")
    style = session.get("style", "casual")

    intro_text = MATT_INTRO.get(interface_lang, MATT_INTRO["en"])
    await context.bot.send_message(chat_id=chat_id, text=intro_text)

    tariff_msg = None
    try:
        prof = get_user_profile(chat_id) or {}
        is_premium = bool(prof.get("is_premium"))
        promo_code_used = session.get("promo_code_used") or prof.get("promo_code_used")
        promo_type = session.get("promo_type") or prof.get("promo_type")
        promo_days = session.get("promo_days") if session.get("promo_days") is not None else prof.get("promo_days")

        from handlers.chat.prompt_templates import get_tariff_intro_msg
        tariff_msg = get_tariff_intro_msg(
            interface_lang,
            is_premium=is_premium,
            promo_code_used=promo_code_used,
            promo_type=promo_type,
            promo_days=promo_days,
            free_daily_limit=15,
        )
        if tariff_msg:
            await context.bot.send_message(chat_id=chat_id, text=tariff_msg)
    except Exception:
        logger.exception("tariff intro message failed")

    question = pick_intro_question(level, style, target_lang)
    await context.bot.send_message(chat_id=chat_id, text=question)

    # --- автоперевод первого вопроса Мэтта при включённой опции ---
    try:
        if session.get("append_translation"):
            from components.translator import do_translate

            ui_lang = session.get("interface_lang", "ru")
            tgt_lang = session.get("target_lang", "en")

            # Определяем направление перевода: если интерфейс ≠ целевой язык,
            # переводим с целевого (язык вопроса) на язык интерфейса.
            direction = "target→ui" if ui_lang != tgt_lang else "ui→target"

            tr_text = await do_translate(
                question,
                interface_lang=ui_lang,
                target_lang=tgt_lang,
                direction=direction,
                style=style,
                level=level,
            )

            # Проверяем, чтобы не дублировать идентичный текст
            if tr_text and tr_text.strip().lower() != question.strip().lower():
                # Перевод выводим в скобках на новой строке
                await context.bot.send_message(chat_id=chat_id, text=f"({tr_text})")
    except Exception as e:
        logger.debug(f"[onboarding_final] auto-translate intro failed: {e}")


    history = session.setdefault("history", [])
    history.append({"role": "assistant", "content": intro_text})
    if tariff_msg:
        history.append({"role": "assistant", "content": tariff_msg})
    history.append({"role": "assistant", "content": question})

    session["onboarding_stage"] = "complete"
