from __future__ import annotations
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from state.session import user_sessions
from components.profile_db import save_user_profile
from components.i18n import get_ui_lang

# Поддерживаемые коды/надписи (короткий локальный справочник)
_LANG_NAMES = {
    "en": "English",  "ru": "Русский", "es": "Español",
    "de": "Deutsch",  "fr": "Français", "sv": "Svenska",
    "fi": "Suomi",
}

def _kb_language() -> InlineKeyboardMarkup:
    codes = ["en","ru","es","de","fr","sv","fi"]
    rows = []
    row = []
    for i, code in enumerate(codes, 1):
        row.append(InlineKeyboardButton(_LANG_NAMES.get(code, code), callback_data=f"CMD:LANG:{code}"))
        if i % 3 == 0:
            rows.append(row); row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def _ok_text(ui: str) -> str:
    return "Готово! Язык для практики: " if ui == "ru" else "Done! Target language: "

async def language_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, ctx)
    prompt = "Выбери язык для изучения:" if ui == "ru" else "Choose a language to learn:"
    await update.effective_message.reply_text(prompt, reply_markup=_kb_language())

async def language_on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    parts = (q.data or "").split(":", 2)
    if len(parts) != 3:
        return
    _, _, code = parts
    chat_id = q.message.chat_id

    sess = user_sessions.setdefault(chat_id, {})
    sess["target_lang"] = code
    try:
        save_user_profile(chat_id, target_lang=code)
    except Exception:
        pass

    ui = get_ui_lang(update, ctx)
    await q.edit_message_text(_ok_text(ui) + _LANG_NAMES.get(code, code))
