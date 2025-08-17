# handlers/commands/language_cmd.py
from __future__ import annotations
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from handlers.settings import LANGS
from components.profile_db import save_user_profile
from components.i18n import get_ui_lang
from state.session import user_sessions

async def language_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, ctx)
    rows = []
    chunk = []
    for title, code in LANGS:
        chunk.append(InlineKeyboardButton(title, callback_data=f"CMD:LANG:{code}"))
        if len(chunk) == 3:
            rows.append(chunk); chunk = []
    if chunk:
        rows.append(chunk)
    await update.effective_message.reply_text(
        "Выбери язык:" if ui == "ru" else "Choose language:",
        reply_markup=InlineKeyboardMarkup(rows)
    )

async def language_on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.data.startswith("CMD:LANG:"):
        return
    await q.answer()
    code = q.data.split(":", 2)[-1]
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Сохраняем ТОЛЬКО язык общения (target_lang). Интерфейсный язык НЕ трогаем.
    ctx.user_data["language"] = code
    save_user_profile(user_id, target_lang=code)

    # Обновляем «живую» сессию — чтобы Мэтт сразу перешёл на новый язык
    sess = user_sessions.setdefault(chat_id, {})
    sess["target_lang"] = code

    ui = get_ui_lang(update, ctx)
    msg = "Готово. Язык общения переключён." if ui == "ru" else "Done. Conversation language switched."
    await q.edit_message_text(msg)
