from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
import aiohttp
import os

from components.admins import ADMIN_IDS

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def _format_stars(amount: int, nano: int | None) -> str:
    nano = int(nano or 0)
    if nano <= 0:
        return str(int(amount))
    frac = f"{nano:09d}".rstrip("0")
    return f"{int(amount)}.{frac}"

async def stars_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id if update.effective_user else None
    if not uid or uid not in ADMIN_IDS:
        await update.message.reply_text("❌ Команда доступна только администратору.")
        return

    if not TELEGRAM_TOKEN:
        await update.message.reply_text("⚠️ TELEGRAM_TOKEN не задан в окружении.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMyStarBalance"

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url) as resp:
                data = await resp.json()

        if not data.get("ok"):
            desc = data.get("description") or "unknown error"
            await update.message.reply_text(f"⚠️ Ошибка при запросе баланса: {desc}")
            return

        res = data.get("result") or {}
        amount = int(res.get("amount", 0))
        nano = int(res.get("nanostar_amount", 0))

        stars_text = _format_stars(amount, nano)
        stars_float = amount + (nano / 1_000_000_000)
        euros = stars_float * 0.01  # 1 Star ~= €0.01

        await update.message.reply_text(
            f"⭐ Баланс бота: {stars_text} Stars\n"
            f"💶 В евро: ~ {euros:.2f} €"
        )

    except Exception as e:
        await update.message.reply_text(f"⚠️ Не удалось получить баланс: {e}")
