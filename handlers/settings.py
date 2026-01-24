from __future__ import annotations
from typing import List, Tuple
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from components.profile_db import get_user_profile, save_user_profile
from components.promo import restrict_target_languages_if_needed, is_promo_valid
from components.i18n import get_ui_lang
from state.session import user_sessions

logger = logging.getLogger(__name__)

# -------------------- Языки --------------------

LANGS: List[Tuple[str, str]] = [
    ("🇷🇺 Русский", "ru"),
    ("🇬🇧 English", "en"),
    ("🇫🇷 Français", "fr"),
    ("🇪🇸 Español", "es"),
    ("🇩🇪 Deutsch", "de"),
    ("🇸🇪 Svenska", "sv"),
    ("🇫🇮 Suomi", "fi"),
]

LEVELS_ROW1 = ["A0", "A1", "A2"]
LEVELS_ROW2 = ["B1", "B2", "C1", "C2"]

STYLE_TITLES = {
    "casual":   {"ru": "😎 Разговорный", "en": "😎 Casual"},
    "business": {"ru": "🤓 Деловой",     "en": "🤓 Business"},
}
STYLE_ORDER = ["casual", "business"]

# -------------------- Helpers --------------------

def _name_for_lang(code: str) -> str:
    for title, c in LANGS:
        if c == code:
            return title
    return code

def _name_for_style(code: str, ui: str) -> str:
    d = STYLE_TITLES.get(code, {})
    return d.get(ui, d.get("ru", code))

def _menu_keyboard(ui: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Язык" if ui == "ru" else "Language",
                                 callback_data="SETTINGS:LANG"),
            InlineKeyboardButton("Уровень" if ui == "ru" else "Level",
                                 callback_data="SETTINGS:LEVEL"),
        ],
        [
            InlineKeyboardButton("Стиль" if ui == "ru" else "Style",
                                 callback_data="SETTINGS:STYLE"),
        ],
        [
            InlineKeyboardButton("✅ OK", callback_data="SETTINGS:CLOSE")
        ],
    ])

def _langs_keyboard(chat_id: int, ui: str) -> InlineKeyboardMarkup:
    prof = get_user_profile(chat_id) or {}
    lang_map = {code: title for title, code in LANGS}
    lang_map = restrict_target_languages_if_needed(prof, lang_map)

    items = [(title, code) for code, title in lang_map.items()]
    rows = []
    for i in range(0, len(items), 2):
        chunk = items[i:i+2]
        rows.append([
            InlineKeyboardButton(t, callback_data=f"SET:LANG:{c}")
            for (t, c) in chunk
        ])

    rows.append([InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back",
                                     callback_data="SETTINGS:BACK")])
    return InlineKeyboardMarkup(rows)

def _levels_keyboard(ui: str) -> InlineKeyboardMarkup:
    row1 = [InlineKeyboardButton(x, callback_data=f"SET:LEVEL:{x}") for x in LEVELS_ROW1]
    row2 = [InlineKeyboardButton(x, callback_data=f"SET:LEVEL:{x}") for x in LEVELS_ROW2]
    back = [InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back",
                                 callback_data="SETTINGS:BACK")]
    return InlineKeyboardMarkup([row1, row2, [back]])

def _styles_keyboard(ui: str) -> InlineKeyboardMarkup:
    rows = []
    for code in STYLE_ORDER:
        title = _name_for_style(code, ui)
        rows.append([InlineKeyboardButton(title, callback_data=f"SET:STYLE:{code}")])
    rows.append([InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back",
                                     callback_data="SETTINGS:BACK")])
    return InlineKeyboardMarkup(rows)

# -------------------- Основные handlers --------------------

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ui = get_ui_lang(update, context)
    chat_id = update.effective_chat.id

    p = get_user_profile(chat_id) or {}
    language = p.get("target_lang", "en")
    level = p.get("level", "B1")
    style = p.get("style", "casual")

    text = (
        f"⚙️ Настройки\n\n"
        f"• Язык: {_name_for_lang(language)}\n"
        f"• Уровень: {level}\n"
        f"• Стиль: {_name_for_style(style, ui)}\n\n"
        f"Что хочешь поменять?"
        if ui == "ru"
        else
        f"⚙️ Settings\n\n"
        f"• Language: {_name_for_lang(language)}\n"
        f"• Level: {level}\n"
        f"• Style: {_name_for_style(style, ui)}\n\n"
        f"What do you want to change?"
    )

    await context.bot.send_message(chat_id, text, reply_markup=_menu_keyboard(ui))

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.data:
        return

    ui = get_ui_lang(update, context)
    chat_id = q.message.chat.id
    data = q.data

    if data == "SETTINGS:CLOSE":
        await q.edit_message_reply_markup(reply_markup=None)
        await q.answer()
        return

    if data == "SETTINGS:BACK":
        await cmd_settings(update, context)
        await q.answer()
        return

    if data == "SETTINGS:LANG":
        await q.edit_message_text(
            "Выбери язык:" if ui == "ru" else "Choose a language:",
            reply_markup=_langs_keyboard(chat_id, ui),
        )
        await q.answer()
        return

    if data == "SETTINGS:LEVEL":
        await q.edit_message_text(
            "Выбери уровень:" if ui == "ru" else "Choose level:",
            reply_markup=_levels_keyboard(ui),
        )
        await q.answer()
        return

    if data == "SETTINGS:STYLE":
        await q.edit_message_text(
            "Выбери стиль:" if ui == "ru" else "Choose style:",
            reply_markup=_styles_keyboard(ui),
        )
        await q.answer()
        return

    if data.startswith("SET:LANG:"):
        code = data.split(":")[-1]
        save_user_profile(chat_id, target_lang=code)
        await q.answer("✅")
        await cmd_settings(update, context)
        return

    if data.startswith("SET:LEVEL:"):
        lev = data.split(":")[-1]
        save_user_profile(chat_id, level=lev)
        await q.answer("✅")
        await cmd_settings(update, context)
        return

    if data.startswith("SET:STYLE:"):
        st = data.split(":")[-1]
        save_user_profile(chat_id, style=st)
        await q.answer("✅")
        await cmd_settings(update, context)
        return


# -------------------- ✅ NEW quick commands --------------------

async def cmd_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /voice — отвечать голосом"""
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    sess["mode"] = "voice"
    await context.bot.send_message(chat_id, "🎙 Теперь отвечаю голосом.")

async def cmd_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /text — отвечать текстом"""
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    sess["mode"] = "text"
    await context.bot.send_message(chat_id, "⌨️ Теперь отвечаю текстом.")
