from __future__ import annotations
from collections import Counter
from telegram import Update
from telegram.ext import ContextTypes

from components.admins import ADMIN_IDS
from state.session import user_sessions

def _top(counter: Counter, n=5):
    return ", ".join(f"{k}:{v}" for k,v in counter.most_common(n)) or "—"

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id if update.effective_user else None
    if not uid or uid not in ADMIN_IDS:
        await update.message.reply_text("⛔")
        return

    # Мини-метрики по текущим сессиям (RAM)
    total_sessions = len(user_sessions)
    modes = Counter()
    task_modes = Counter()
    iface = Counter()
    target = Counter()
    levels = Counter()
    translator_on = 0

    for _, sess in user_sessions.items():
        modes[sess.get("mode","?")] += 1
        tm = sess.get("task_mode","chat")
        task_modes[tm] += 1
        iface[sess.get("interface_lang","?")] += 1
        target[sess.get("target_lang","?")] += 1
        levels[sess.get("level","?")] += 1
        if tm == "translator":
            translator_on += 1

    text = (
        "📊 Runtime stats (RAM):\n"
        f"Сессии в памяти: {total_sessions}\n"
        f"mode top: {_top(modes)}\n"
        f"task_mode top: {_top(task_modes)} (translator:{translator_on})\n"
        f"interface top: {_top(iface)}\n"
        f"target top: {_top(target)}\n"
        f"levels: {_top(levels)}\n"
    )
    await update.message.reply_text(text)
