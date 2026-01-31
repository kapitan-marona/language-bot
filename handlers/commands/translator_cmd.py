# handlers/commands/translator_cmd.py
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from state.session import user_sessions
from handlers.translator_mode import enter_translator, exit_translator


def _get_session_for_update(update: Update) -> dict:
    """Единый источник сессии: по user_id, с алиасом по chat_id (для обратной совместимости)."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    sess = user_sessions.get(user_id)
    if sess is None:
        # fallback на старый ключ (chat_id), если уже был создан ранее
        sess = user_sessions.get(chat_id)
        if sess is None:
            sess = {}
        user_sessions[user_id] = sess

    # алиас: чтобы код, который ещё читает по chat_id, видел ту же самую сессию
    if chat_id != user_id:
        user_sessions[chat_id] = sess

    return sess


async def translator_on_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sess = _get_session_for_update(update)
    await enter_translator(update, ctx, sess)


async def translator_off_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sess = _get_session_for_update(update)
    await exit_translator(update, ctx, sess)
