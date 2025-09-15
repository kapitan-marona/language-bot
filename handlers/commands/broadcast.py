from __future__ import annotations
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from components.admins import ADMIN_IDS
from components.profile_db import get_all_chat_ids

RATE_DELAY_SEC = 0.05  # ~20 msg/сек, чтобы не упереться в лимиты

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id if update.effective_user else None
    if not uid or uid not in ADMIN_IDS:
        await update.message.reply_text("⛔️")
        return

    # текст берём либо из аргументов команды, либо из reply на чьё-то сообщение
    text = " ".join(context.args).strip() if context.args else ""
    if not text and update.message and update.message.reply_to_message:
        text = (update.message.reply_to_message.text or "").strip()

    if not text:
        await update.message.reply_text("Введите текст после команды или сделайте /broadcast как reply к сообщению.")
        return

    try:
        chat_ids = get_all_chat_ids()
    except Exception:
        await update.message.reply_text("⚠️ Не удалось получить список пользователей.")
        return

    sent = 0
    failed = 0
    for chat_id in chat_ids:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(RATE_DELAY_SEC)

    await update.message.reply_text(f"Рассылка завершена ✅\nОтправлено: {sent}\nОшибок: {failed}\nВсего: {len(chat_ids)}")
