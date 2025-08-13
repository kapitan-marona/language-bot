from __future__ import annotations
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from handlers.settings import STYLES
from components.profile_db import save_user_profile

def _ui_lang(ctx: ContextTypes.DEFAULT_TYPE) -> str:
    return ctx.user_data.get("ui_lang", "ru")

async def style_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = _ui_lang(ctx)
    rows = [[InlineKeyboardButton(title, callback_data=f"CMD:STYLE:{code}")] for title, code in STYLES]
    await update.effective_message.reply_text(
        "Выбери стиль общения:" if ui == "ru" else "Choose chat style:",
        reply_markup=InlineKeyboardMarkup(rows)
    )

async def style_on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.data.startswith("CMD:STYLE:"):
        return
    await q.answer()
    style = q.data.split(":", 2)[-1]
    chat_id = update.effective_chat.id

    ctx.user_data["style"] = style
    save_user_profile(chat_id, style=style)

    ui = _ui_lang(ctx)
    await q.edit_message_text(
        "Готово. Стиль сохранён." if ui == "ru" else "Done. Style saved."
    )
