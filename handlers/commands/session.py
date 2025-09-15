from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes

from components.admins import ADMIN_IDS
from state.session import user_sessions

async def session_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id if update.effective_user else None
    if not uid or uid not in ADMIN_IDS:
        await update.message.reply_text("⛔")
        return

    chat_id = update.effective_chat.id
    sess = user_sessions.get(chat_id, {})
    if not sess:
        await update.message.reply_text("Сессия не найдена для этого чата.")
        return

    translator = sess.get("translator") or {}
    text = (
        "🧭 Session info:\n"
        f"mode: {sess.get('mode')}\n"
        f"task_mode: {sess.get('task_mode')}\n"
        f"interface_lang: {sess.get('interface_lang')}\n"
        f"target_lang: {sess.get('target_lang')}\n"
        f"level: {sess.get('level')}\n"
        f"history_len: {len(sess.get('history', []))}\n"
        f"translator: dir={translator.get('direction')}, style={translator.get('style')}, output={translator.get('output')}\n"
        f"last_assistant_text: {len((sess.get('last_assistant_text') or ''))} chars\n"
    )
    await update.message.reply_text(text)
