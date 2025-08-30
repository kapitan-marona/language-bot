from telegram import Update
from telegram.ext import ContextTypes
import aiohttp
import os

from components.admins import ADMIN_IDS

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def stars_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id if update.effective_user else None
    if not uid or uid not in ADMIN_IDS:
        await update.message.reply_text("❌ Команда доступна только администратору.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMyStarBalance"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        if data.get("ok"):
            balance = data["result"]["stars"]
            euros = balance / 100  # 1 Star = 0.01 €
            await update.message.reply_text(
                f"⭐ Баланс бота: {balance} Stars\n"
                f"💶 В евро: ~ {euros:.2f} €"
            )
        else:
            await update.message.reply_text(f"⚠️ Ошибка при запросе баланса:\n{data}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка соединения: {e}")
