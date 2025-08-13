from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Literal
from telegram import LabeledPrice, Update
from telegram.ext import ContextTypes
from components.profile_db import save_user_profile, get_user_profile
from components.i18n import get_ui_lang  # NEW

Product = Literal["pro_30d"]

XTR_CURRENCY = "XTR"  # Stars валюта

def plan_price_xtr(product: Product) -> list[LabeledPrice]:
    if product == "pro_30d":
        return [LabeledPrice(label="30 days", amount=149)]
    raise ValueError("Unknown product")

def compute_expiry(profile: dict | None, days: int = 30) -> datetime:
    """
    Продлеваем от текущей даты, если подписки нет или истекла,
    либо от текущего expiry, если он в будущем.
    """
    now = datetime.now(timezone.utc)
    base = now
    if profile:
        expires = profile.get("premium_expires_at")
        if expires:
            try:
                dt = datetime.fromisoformat(expires)
                if dt.tzinfo is None:                # NEW: приводим к TZ-aware, если не было таймзоны
                    dt = dt.replace(tzinfo=timezone.utc)
                base = dt if dt > now else now       # NEW: берём максимум (исправляет редкие ошибки сравнения)
            except Exception:
                pass
    return base + timedelta(days=days)

async def send_stars_invoice(update: Update, ctx: ContextTypes.DEFAULT_TYPE, product: Product) -> None:
    # NEW: локализуем заголовок/описание счёта по текущему UI-языку
    ui = get_ui_lang(update, ctx)                    # NEW
    title = "English Talking — 30 дней" if ui == "ru" else "English Talking — 30 days"  # CHANGED
    desc = ("Безлимитные диалоги в тексте и голосе на 30 дней."
            if ui == "ru"
            else "Unlimited text & voice chats for 30 days.")                           # CHANGED
    payload = f"{product}:{update.effective_user.id}"

    await update.effective_chat.send_invoice(
        title=title,
        description=desc,
        payload=payload,
        provider_token="",       # пустая строка для Stars — корректно
        currency=XTR_CURRENCY,
        prices=plan_price_xtr(product),
        # start_parameter="premium_30d",            # NEW (опционально): если используешь deep-linking
    )

async def precheckout_ok(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.pre_checkout_query.answer(ok=True)

async def on_successful_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    sp = update.message.successful_payment
    if not sp:                                       # NEW: защита от редких кейсов без объекта оплаты
        return
    profile = get_user_profile(update.effective_user.id)
    until = compute_expiry(profile, days=30)
    save_user_profile(
        update.effective_user.id,
        is_premium=1,
        premium_expires_at=until.isoformat(),
        last_payment_charge_id=sp.telegram_payment_charge_id,
    )
    ui = get_ui_lang(update, ctx)                    # CHANGED: берём язык через общий резолвер
    msg = (
        f"✅ Оплата прошла! Доступ активен до {until.date().isoformat()}. Приятной практики!"
        if ui == "ru"
        else f"✅ Payment complete! Access active until {until.date().isoformat()}. Enjoy!"
    )
    await update.message.reply_text(msg)
