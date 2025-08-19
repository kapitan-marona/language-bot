from __future__ import annotations
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from handlers.settings import LEVELS_ROW1, LEVELS_ROW2
from components.profile_db import save_user_profile

def _ui_lang(ctx: ContextTypes.DEFAULT_TYPE) -> str:
    return ctx.user_data.get("ui_lang", "ru")

async def level_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = _ui_lang(ctx)
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

    ctx.user_data["level"] = level
    save_user_profile(chat_id, level=level)

    ui = _ui_lang(ctx)
    await q.edit_message_text(
        f"Готово. Уровень: {level}" if ui == "ru" else f"Done. Level: {level}"
    )
