from __future__ import annotations
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from state.session import user_sessions
from components.profile_db import save_user_profile
from components.i18n import get_ui_lang

_LEVELS = ["A0","A1","A2","B1","B2","C1","C2"]

def _kb_levels() -> InlineKeyboardMarkup:
    rows = []
    # два ряда по 4 и 3
    rows.append([InlineKeyboardButton(l, callback_data=f"CMD:LEVEL:{l}") for l in _LEVELS[:4]])
    rows.append([InlineKeyboardButton(l, callback_data=f"CMD:LEVEL:{l}") for l in _LEVELS[4:]])
    return InlineKeyboardMarkup(rows)

async def level_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, ctx)
    prompt = "Выбери уровень:" if ui == "ru" else "Choose your level:"
    await update.effective_message.reply_text(prompt, reply_markup=_kb_levels())

async def level_on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    parts = (q.data or "").split(":", 2)
    if len(parts) != 3:
        return
    _, _, lev = parts
    chat_id = q.message.chat_id

    sess = user_sessions.setdefault(chat_id, {})
    sess["level"] = lev
    try:
        save_user_profile(chat_id, level=lev)
    except Exception:
        pass

    ui = get_ui_lang(update, ctx)
    msg = "Готово! Уровень: " if ui == "ru" else "Done! Level: "
    await q.edit_message_text(msg + lev)
