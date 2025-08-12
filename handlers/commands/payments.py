from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timezone
from components.profile_db import get_user_profile
from components.payments import send_stars_invoice

async def buy_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    profile = get_user_profile(update.effective_user.id)
    if profile and profile.get("premium_expires_at"):
        try:
            until = datetime.fromisoformat(profile["premium_expires_at"])
            if until > datetime.now(timezone.utc):
                ui = ctx.user_data.get("ui_lang", "ru")
                msg = ("У тебя уже активен доступ до {d}"
                       if ui == "ru" else
                       "You already have access until {d}").format(d=until.date().isoformat())
                await update.message.reply_text(msg)
                return
        except Exception:
            pass
    await send_stars_invoice(update, ctx, product="pro_30d")
