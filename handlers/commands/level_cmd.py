# handlers/commands/level_cmd.py
from __future__ import annotations
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from handlers.settings import LEVELS_ROW1, LEVELS_ROW2
from components.profile_db import save_user_profile
from components.i18n import get_ui_lang
from state.session import user_sessions

async def level_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, ctx)
    row1 = [InlineKeyboardButton(x, callback_data=f"CMD:LEVEL:{x}") for x in LEVELS_ROW1]
    row2 = [InlineKeyboardButton(x, callback_data=f"CMD:LEVEL:{x}") for x in LEVELS_ROW2]
    await update.effective_message.reply_text(
        "Выбери уровень:" if ui == "ru" else "Choose your level:",
        reply_markup=InlineKeyboardMarkup([row1, row2])
    )

async def level_on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.data.startswith("CMD:LEVEL:"):
        return
    await q.answer()
    level = q.data.split(":", 2)[-1]
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    ctx.user_data["level"] = level
    save_user_profile(user_id, level=level)

    # синхронизируем активную сессию
    sess = user_sessions.setdefault(chat_id, {})
    sess["level"] = level

    ui = get_ui_lang(update, ctx)
    await q.edit_message_text(
        f"Готово. Уровень: {level}" if ui == "ru" else f"Done. Level: {level}"
    )
