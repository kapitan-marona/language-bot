from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes

async def menu_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.data:
        return
    await q.answer()
    data = q.data
    if data == "open:donate":
        await q.message.chat.send_message("/donate")
    elif data == "open:promo":
        await q.message.chat.send_message("/promo")
    elif data == "open:sub":
        await q.message.chat.send_message("/buy")
