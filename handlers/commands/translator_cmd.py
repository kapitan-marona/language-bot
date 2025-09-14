# handlers/commands/translator_cmd.py
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes

from state.session import user_sessions
from handlers.translator_mode import enter_translator, exit_translator

async def translator_on_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    await enter_translator(update, ctx, sess)

async def translator_off_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    await exit_translator(update, ctx, sess)
