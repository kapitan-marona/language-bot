from __future__ import annotations
import os, time
from telegram import Update
from telegram.ext import ContextTypes

from components.admins import ADMIN_IDS

START_TS = time.time()
ENV = os.getenv("ENV","dev")

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id if update.effective_user else None
    if not uid or uid not in ADMIN_IDS:
        await update.message.reply_text("⛔")
        return

    uptime = int(time.time() - START_TS)
    await update.message.reply_text(
        "✅ ok\n"
        f"env: {ENV}\n"
        f"uptime: {uptime}s"
    )
