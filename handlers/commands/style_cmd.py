# handlers/commands/style_cmd.py
from __future__ import annotations
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from handlers.settings import STYLES
from components.profile_db import save_user_profile
from components.i18n import get_ui_lang
from state.session import user_sessions

async def style_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, ctx)
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
    user_id = update.effective_user.id

    ctx.user_data["style"] = style
    save_user_profile(user_id, style=style)

    # синхронизируем активную сессию
    sess = user_sessions.setdefault(chat_id, {})
    sess["style"] = style

    ui = get_ui_lang(update, ctx)
    await q.edit_message_text(
        "Готово. Стиль сохранён." if ui == "ru" else "Done. Style saved."
    )
