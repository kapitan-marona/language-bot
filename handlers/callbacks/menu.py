from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from handlers import settings
from handlers.commands.promo import promo_command
from handlers.commands.donate import donate_command
from handlers.commands.teach import glossary_cmd   # ← teach_start больше не импортируем
from handlers.commands.payments import buy_command

async def menu_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.data:
        return
    await q.answer()
    data = q.data

    if data == "open:settings":
        await settings.cmd_settings(update, ctx)
    elif data == "open:donate":
        await donate_command(update, ctx)
    elif data == "open:promo":
        await promo_command(update, ctx)
    elif data == "open:sub":
        await buy_command(update, ctx)
    elif data == "open:teach":
        # Ничего не делаем здесь — вход в разговор обрабатывает ConversationHandler
        # (см. entry point в handlers/commands/teach.py)
        return
    elif data == "open:glossary":
        await glossary_cmd(update, ctx)
