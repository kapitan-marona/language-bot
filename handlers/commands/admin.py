from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes

from components.admins import ADMIN_IDS  # единый источник админов (из ENV)
from state.session import user_sessions

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id or user_id not in ADMIN_IDS:
        await update.effective_message.reply_text("⛔️")
        return

    chat_id = update.effective_chat.id
    user_sessions.setdefault(chat_id, {})  # на будущее

    await update.effective_message.reply_text(
        "👑 Админ-панель:\n"
        "/users — кол-во пользователей\n"
        "/user — стать обычным\n"
        "/reset — сбросить профиль\n"
        "/test — тестовая команда\n"
        "/broadcast — рассылка\n"
        "/promo — промокоды\n"
        "/stats — статистика\n"
        "/session — инфо о сессии\n"
        "/help — список команд"
    )
