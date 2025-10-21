# handlers/commands/db_info.py
from __future__ import annotations
import os, sqlite3
from telegram import Update
from telegram.ext import ContextTypes
from components.admins import ADMIN_IDS
from components.profile_db import DB_PATH as PROFILES_DB_PATH

def _is_admin(update: Update) -> bool:
    u = update.effective_user
    return bool(u and u.id in ADMIN_IDS)

async def db_info_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return await update.message.reply_text("⛔️")
    path = PROFILES_DB_PATH
    exists = os.path.exists(path)
    if not exists:
        return await update.message.reply_text(f"📦 DB: {path}\n❌ Файл не найден")

    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cur.fetchall()]
    counts = {}
    for t in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            counts[t] = cur.fetchone()[0]
        except Exception:
            counts[t] = "n/a"
    con.close()

    lines = [f"📦 DB: {path}", "📑 Таблицы:"]
    for t in sorted(tables):
        lines.append(f"• {t}: {counts[t]}")
    await update.message.reply_text("\n".join(lines))
