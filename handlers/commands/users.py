from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes

from components.admins import ADMIN_IDS
from components.profile_db import get_all_chat_ids

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id if update.effective_user else None
    if not uid or uid not in ADMIN_IDS:
        await update.message.reply_text("⛔")
        return

    try:
        chat_ids = get_all_chat_ids()
        total = len(chat_ids)
    except Exception:
        await update.message.reply_text("⚠️ Не удалось получить список пользователей.")
        return

    await update.message.reply_text(f"👥 Пользователей: {total}")
