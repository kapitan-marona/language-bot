# handlers/commands/db_health.py
from __future__ import annotations
import os, sqlite3
from telegram import Update
from telegram.ext import ContextTypes
from components.admins import ADMIN_IDS
from components.profile_db import DB_PATH as PROFILES_DB_PATH

async def db_health_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not (update.effective_user and update.effective_user.id in ADMIN_IDS):
        return await update.message.reply_text("⛔️")

    path = PROFILES_DB_PATH
    if not os.path.exists(path):
        return await update.message.reply_text("❌ DB файл не найден")

    con = sqlite3.connect(path, timeout=5)
    cur = con.cursor()
    # целостность
    cur.execute("PRAGMA integrity_check;")
    integrity = cur.fetchone()[0]
    # размер
    size_mb = os.path.getsize(path) / (1024*1024)
    # режим журнала
    cur.execute("PRAGMA journal_mode;")
    journal = cur.fetchone()[0]
    con.close()

    await update.message.reply_text(
        f"🩺 integrity_check: {integrity}\n"
        f"📏 size: {size_mb:.2f} MB\n"
        f"📓 journal_mode: {journal}"
    )
