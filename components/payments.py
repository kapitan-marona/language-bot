from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Literal
from telegram import LabeledPrice, Update
from telegram.ext import ContextTypes
from components.profile_db import save_user_profile, get_user_profile

Product = Literal["pro_30d"]

XTR_CURRENCY = "XTR"  # Stars валюта

def plan_price_xtr(product: Product) -> list[LabeledPrice]:
    if product == "pro_30d":
        return [LabeledPrice(label="30 days", amount=149)]
    raise ValueError("Unknown product")

def compute_expiry(profile: dict | None, days: int = 30) -> datetime:
    now = datetime.now(timezone.utc)
    base = now
    if profile:
        expires = profile.get("premium_expires_at")
        if expires:
            try:
                dt = datetime.fromisoformat(expires)
                if dt > now:
                    base = dt
            except Exception:
                pass
    return base + timedelta(days=days)

async def send_stars_invoice(update: Update, ctx: ContextTypes.DEFAULT_TYPE, product: Product) -> None:
    title = "English Talking — 30 дней"
    desc = "Безлимитные диалоги в тексте и голосе на 30 дней."
    payload = f"{product}:{update.effective_user.id}"

    await update.effective_chat.send_invoice(
        title=title,
        description=desc,
        payload=payload,
        provider_token="",  # пустая строка для Stars
        currency=XTR_CURRENCY,
        prices=plan_price_xtr(product),
    )

async def precheckout_ok(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.pre_checkout_query.answer(ok=True)

async def on_successful_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    sp = update.message.successful_payment
    profile = get_user_profile(update.effective_user.id)
    until = compute_expiry(profile, days=30)
    save_user_profile(
        update.effective_user.id,
        is_premium=1,
        premium_expires_at=until.isoformat(),
        last_payment_charge_id=sp.telegram_payment_charge_id,
    )
    ui = ctx.user_data.get("ui_lang", "ru")
    msg = (
        f"✅ Оплата прошла! Доступ активен до {until.date().isoformat()}. Приятной практики!"
        if ui == "ru"
        else f"✅ Payment complete! Access active until {until.date().isoformat()}. Enjoy!"
    )
    await update.message.reply_text(msg)
