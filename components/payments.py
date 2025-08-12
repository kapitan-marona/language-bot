from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Literal
from telegram import LabeledPrice, Update
from telegram.ext import ContextTypes
from components.profile_db import save_user_profile, get_user_profile

Product = Literal["pro_30d"]
XTR_CURRENCY = "XTR"

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

async def send_stars_invoice(update: Update, ctx: ContextTypes.DEFAULT_TYPE, product: Product = "pro_30d") -> None:
    # Тексты вынесли излишне — оставим прямо тут, чтобы не ловить ещё один импорт
    ui = ctx.user_data.get("ui_lang", "ru")
    title = "Доступ English Talking — 30 дней" if ui == "ru" else "English Talking Access — 30 days"
    desc  = "Подписка на 30 дней: безлимитные диалоги в тексте и голосе." if ui == "ru" else "30-day access: unlimited text & voice practice."
    prices = plan_price_xtr(product)
    payload = f"{product}:{update.effective_user.id}"
    await update.effective_chat.send_invoice(
        title=title,
        description=desc,
        payload=payload,
        currency=XTR_CURRENCY,
        prices=prices,
        api_kwargs={},  # для Stars provider_token не нужен
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
    msg = ("✅ Оплата прошла! Доступ активен до {d}. Приятной практики!"
           if ui == "ru" else
           "✅ Payment complete! Access active until {d}. Enjoy!").format(d=until.date().isoformat())
    await update.message.reply_text(msg)
