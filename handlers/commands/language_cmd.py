from __future__ import annotations
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from handlers.settings import LANGS
from components.profile_db import save_user_profile

def _ui_lang(ctx: ContextTypes.DEFAULT_TYPE) -> str:
    return ctx.user_data.get("ui_lang", "ru")

async def language_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = _ui_lang(ctx)
    rows = []
    chunk = []
    for title, code in LANGS:
        chunk.append(InlineKeyboardButton(title, callback_data=f"CMD:LANG:{code}"))
        if len(chunk) == 3:
            rows.append(chunk); chunk = []
    if chunk:
        rows.append(chunk)
    await update.effective_message.reply_text(
        "Выбери язык интерфейса/практики:" if ui == "ru" else "Choose interface/practice language:",
        reply_markup=InlineKeyboardMarkup(rows)
    )

async def language_on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.data.startswith("CMD:LANG:"):
        return
    await q.answer()
    code = q.data.split(":", 2)[-1]
    chat_id = update.effective_chat.id

    ctx.user_data["language"] = code
    ctx.user_data["ui_lang"] = code
    save_user_profile(chat_id, target_lang=code, interface_lang=code)

    msg = "Готово. Язык переключён." if code == "ru" else "Done. Language switched."
    await q.edit_message_text(msg)
