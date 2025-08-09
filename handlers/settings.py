# handlers/settings.py
from __future__ import annotations
from typing import List, Tuple
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from components.profile_db import get_user_profile, save_user_profile
from components.promo import restrict_target_languages_if_needed, is_promo_valid
# (импорты оставил как были; промо-обработку ввода делаем в english_bot.py)

logger = logging.getLogger(__name__)

# Языки (флаг + название)
LANGS: List[Tuple[str, str]] = [
    ("🇷🇺 Русский", "ru"),
    ("🇬🇧 English", "en"),
    ("🇫🇷 Français", "fr"),
    ("🇪🇸 Español", "es"),
    ("🇩🇪 Deutsch", "de"),
    ("🇸🇪 Svenska", "sv"),
    ("🇫🇮 Suomi", "fi"),
]

# Уровни
LEVELS_ROW1 = ["A0", "A1", "A2"]
LEVELS_ROW2 = ["B1", "B2", "C1", "C2"]

# Стили
STYLES: List[Tuple[str, str]] = [
    ("😎 Разговорный", "casual"),
    ("🤓 Деловой", "business"),
]

def _ui_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Язык интерфейса (по умолчанию RU)."""
    try:
        return (context.user_data or {}).get("ui", "ru")
    except Exception:
        return "ru"

def _name_for_lang(code: str) -> str:
    m = {"ru":"Русский","en":"English","fr":"Français","es":"Español","de":"Deutsch","sv":"Svenska","fi":"Suomi"}
    return m.get(code, code)

def _name_for_style(code: str) -> str:
    return {"casual":"Разговорный","business":"Деловой"}.get(code, code)

def _main_menu_text(ui: str, language_name: str, level: str, style_name: str, english_only_note: bool) -> str:
    if ui == "ru":
        note = "\n\n⚠️ Доступен только английский (промо English-only)." if english_only_note else ""
        return f"⚙️ Настройки\nЯзык: {language_name}\nУровень: {level}\nСтиль: {style_name}{note}"
    else:
        note = "\n\n⚠️ Only English available (English-only promo)." if english_only_note else ""
        return f"⚙️ Settings\nLanguage: {language_name}\nLevel: {level}\nStyle: {style_name}{note}"

def _lang_keyboard(ui: str) -> InlineKeyboardMarkup:
    btns = [[InlineKeyboardButton(title, callback_data=f"SET:LANG:{code}")]
            for (title, code) in LANGS]
    return InlineKeyboardMarkup(btns)

def _level_keyboard(ui: str) -> InlineKeyboardMarkup:
    btns = [
        [InlineKeyboardButton(x, callback_data=f"SET:LEVEL:{x}") for x in LEVELS_ROW1],
        [InlineKeyboardButton(x, callback_data=f"SET:LEVEL:{x}") for x in LEVELS_ROW2],
    ]
    return InlineKeyboardMarkup(btns)

def _style_keyboard(ui: str) -> InlineKeyboardMarkup:
    btns = [[InlineKeyboardButton(title, callback_data=f"SET:STYLE:{code}")]
            for (title, code) in STYLES]
    return InlineKeyboardMarkup(btns)

def _menu_keyboard(ui: str, has_pending: bool = False) -> InlineKeyboardMarkup:  # NEW: has_pending flag
    btns = [
        [InlineKeyboardButton("🌐 Язык / Language" if ui == "ru" else "🌐 Language / Язык", callback_data="SETTINGS:LANG")],
        [InlineKeyboardButton("🎯 Уровень" if ui == "ru" else "🎯 Level", callback_data="SETTINGS:LEVEL")],
        [InlineKeyboardButton("🎭 Стиль" if ui == "ru" else "🎭 Style", callback_data="SETTINGS:STYLE")],
        [InlineKeyboardButton("🏷️ Промокод" if ui == "ru" else "🏷️ Promo", callback_data="SETTINGS:PROMO")],
    ]
    # NEW: show confirm button only if there are unsaved changes
    if has_pending:
        btns.append([InlineKeyboardButton("✅ Готово" if ui == "ru" else "✅ Done", callback_data="SETTINGS:CONFIRM")])
    return InlineKeyboardMarkup(btns)

# Вход в настройки (через /help или кнопку «Настройки»)
async def settings_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ui = _ui_lang(context)
    chat_id = update.effective_chat.id

    p = get_user_profile(chat_id) or {}
    s = context.user_data or {}

    language = p.get("target_lang") or s.get("language") or "en"   # NEW: DB — источник истины
    level = p.get("level") or s.get("level") or "B1"                # NEW
    style = p.get("style") or s.get("style") or "neutral"           # NEW
    english_only_note = (p.get("promo_type") == "english_only" and is_promo_valid(p))
    has_pending = bool((context.user_data or {}).get("pending_changes"))  # NEW

    await update.message.reply_text(
        _main_menu_text(ui, _name_for_lang(language), level, _name_for_style(style), english_only_note),
        reply_markup=_menu_keyboard(ui, has_pending),  # NEW: pass has_pending
    )

# Обработка нажатий в настройках
async def settings_on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    ui = _ui_lang(context)
    chat_id = q.message.chat_id

    # ЯЗЫК
    if data.startswith("SET:LANG:"):
        lang_code = data.split(":", 2)[-1]
        pending = context.user_data.setdefault("pending_changes", {})  # NEW
        pending["target_lang"] = lang_code  # NEW
        await q.answer("ОК")  # NEW: defer save until CONFIRM

        p = get_user_profile(chat_id) or {}
        s = context.user_data or {}
        language = pending.get("target_lang") or p.get("target_lang") or s.get("language") or "en"  # NEW
        level = pending.get("level") or p.get("level") or s.get("level") or "B1"                     # NEW
        style = pending.get("style") or p.get("style") or s.get("style") or "neutral"                # NEW
        english_only_note = (p.get("promo_type") == "english_only" and is_promo_valid(p))
        await q.edit_message_text(
            _main_menu_text(ui, _name_for_lang(language), level, _name_for_style(style), english_only_note),
            reply_markup=_menu_keyboard(ui, has_pending=True),  # NEW
        )
        return

    # УРОВЕНЬ
    if data.startswith("SET:LEVEL:"):
        level = data.split(":", 2)[-1]
        pending = context.user_data.setdefault("pending_changes", {})  # NEW
        pending["level"] = level  # NEW
        await q.answer("ОК")  # NEW: defer save until CONFIRM

        p = get_user_profile(chat_id) or {}
        s = context.user_data or {}
        language = pending.get("target_lang") or p.get("target_lang") or s.get("language") or "en"  # NEW
        level = pending.get("level") or p.get("level") or s.get("level") or "B1"                     # NEW
        style = pending.get("style") or p.get("style") or s.get("style") or "neutral"                # NEW
        english_only_note = (p.get("promo_type") == "english_only" and is_promo_valid(p))
        await q.edit_message_text(
            _main_menu_text(ui, _name_for_lang(language), level, _name_for_style(style), english_only_note),
            reply_markup=_menu_keyboard(ui, has_pending=True),  # NEW
        )
        return

    # СТИЛЬ
    if data.startswith("SET:STYLE:"):
        style = data.split(":", 2)[-1]
        pending = context.user_data.setdefault("pending_changes", {})  # NEW
        pending["style"] = style  # NEW
        await q.answer("ОК")  # NEW: defer save until CONFIRM

        p = get_user_profile(chat_id) or {}
        s = context.user_data or {}
        language = pending.get("target_lang") or p.get("target_lang") or s.get("language") or "en"  # NEW
        level = pending.get("level") or p.get("level") or s.get("level") or "B1"                     # NEW
        style = pending.get("style") or p.get("style") or s.get("style") or "neutral"                # NEW
        english_only_note = (p.get("promo_type") == "english_only" and is_promo_valid(p))
        await q.edit_message_text(
            _main_menu_text(ui, _name_for_lang(language), level, _name_for_style(style), english_only_note),
            reply_markup=_menu_keyboard(ui, has_pending=True),  # NEW
        )
        return

    # ✅ Готово — записать все pending в БД
    if data == "SETTINGS:CONFIRM":  # NEW
        pending = (context.user_data or {}).get("pending_changes") or {}  # NEW
        if pending:  # NEW
            save_user_profile(  # NEW
                chat_id,        # NEW
                target_lang=pending.get("target_lang"),  # NEW
                level=pending.get("level"),              # NEW
                style=pending.get("style"),              # NEW
            )  # NEW
            context.user_data["pending_changes"] = {}  # NEW
        p = get_user_profile(chat_id) or {}  # NEW
        language = p.get("target_lang") or "en"  # NEW
        level = p.get("level") or "B1"           # NEW
        style = p.get("style") or "neutral"      # NEW
        english_only_note = (p.get("promo_type") == "english_only" and is_promo_valid(p))  # NEW
        await q.edit_message_text(  # NEW
            _main_menu_text(ui, _name_for_lang(language), level, _name_for_style(style), english_only_note),  # NEW
            reply_markup=_menu_keyboard(ui, has_pending=False),  # NEW
        )  # NEW
        await q.answer("Сохранено" if ui == "ru" else "Saved")  # NEW
        return  # NEW

    # Промокод — просим ввести код текстом
    if data == "SETTINGS:PROMO":
        await q.answer()
        context.user_data["awaiting_promo"] = True  # NEW: expect text promo code
        await q.edit_message_text("Введите промокод текстом:" if ui == "ru" else "Please type your promo code:")  # NEW
        return
