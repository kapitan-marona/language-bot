# components/payments.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Literal

from telegram import LabeledPrice, Update
from telegram.ext import ContextTypes

from components.profile_db import save_user_profile, get_user_profile
from components.i18n import get_ui_lang
from components.config_store import get_kv  # >>> ADDED

Product = Literal["pro_30d"]

XTR_CURRENCY = "XTR"  # Stars валюта

def _price_stars() -> int:
    """
    Текущая цена в звёздах. Если в config_store ключа нет — дефолт 1000.
    """
    try:
        val = int(get_kv("price_stars", 1000))  # >>> ADDED
        return max(1, val)
    except Exception:
        return 1000

def plan_price_xtr(product: Product) -> list[LabeledPrice]:
    if product == "pro_30d":
        return [LabeledPrice(label="30 days", amount=_price_stars())]  # >>> CHANGED
    raise ValueError("Unknown product")

def compute_expiry(profile: dict | None, days: int = 30) -> datetime:
    """
    Продлеваем от текущей даты, если подписки нет/истекла,
    либо от текущего expiry, если он в будущем.
    """
    now = datetime.now(timezone.utc)
    base = now
    if profile:
        expires_iso = profile.get("premium_until")  # >>> CHANGED (поле БД)
        if expires_iso:
            try:
                dt = datetime.fromisoformat(str(expires_iso).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                base = dt if dt > now else now
            except Exception:
                pass
    return base + timedelta(days=days)

# ------------------- PRO (покупка) -------------------

async def send_stars_invoice(update: Update, ctx: ContextTypes.DEFAULT_TYPE, product: Product) -> None:
    ui = get_ui_lang(update, ctx)
    title = "English Talking — 30 дней" if ui == "ru" else "English Talking — 30 days"
    desc = ("Безлимитные диалоги в тексте и голосе на 30 дней."
            if ui == "ru"
            else "Unlimited text & voice chats for 30 days.")
    payload = f"{product}:{update.effective_user.id}"

    await update.effective_chat.send_invoice(
        title=title,
        description=desc,
        payload=payload,
        provider_token="",          # Stars
        currency=XTR_CURRENCY,
        prices=plan_price_xtr(product),
    )

# ------------------- DONATION (донаты) -------------------

async def send_donation_invoice(update: Update, ctx: ContextTypes.DEFAULT_TYPE, amount: int) -> None:
    ui = get_ui_lang(update, ctx)
    title = "Пожертвование проекту" if ui == "ru" else "Donation to the Project"
    desc = ("Спасибо за поддержку! Это добровольный взнос в звёздах."
            if ui == "ru" else
            "Thank you for your support! This is a voluntary donation in Stars.")
    payload = f"donation:{amount}:{update.effective_user.id}"
    prices = [LabeledPrice(label="Donation", amount=int(amount))]

    await update.effective_chat.send_invoice(
        title=title,
        description=desc,
        payload=payload,
        provider_token="",   # Stars
        currency=XTR_CURRENCY,
        prices=prices,
    )

# ------------------- Общие платёжные хендлеры -------------------

async def precheckout_ok(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.pre_checkout_query.answer(ok=True)

async def on_successful_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    sp = getattr(update.message, "successful_payment", None)
    if not sp:
        return

    # Снимаем флаг «жду сумму доната», чтобы чат не вмешивался
    try:
        if getattr(ctx, "user_data", None) and ctx.user_data.get("donate_wait_amount"):  # >>> ADDED
            ctx.user_data.pop("donate_wait_amount", None)                                 # >>> ADDED
    except Exception:
        pass

    payload = sp.invoice_payload or ""

    # --- Донат: просто благодарим ---
    if payload.startswith("donation:"):
        try:
            _, amount_str, _ = payload.split(":", 2)
            amount = int(amount_str)
        except Exception:
            amount = sp.total_amount or 0
        ui = get_ui_lang(update, ctx)
        msg = (f"🙏 Спасибо за поддержку! Получено {amount}⭐"
               if ui == "ru" else
               f"🙏 Thank you for your support! Received {amount}⭐")
        await update.message.reply_text(msg)
        return

    # --- Покупка тарифа (30 дней) ---
    if not payload.startswith("pro_30d:"):
        return

    # чек должен быть для этого же пользователя
    try:
        _, uid_str = payload.split(":", 1)
        if int(uid_str) != update.effective_user.id:
            return
    except Exception:
        return

    # проверяем валюту и сумму
    expected = _price_stars()  # >>> CHANGED
    if sp.currency != XTR_CURRENCY or int(sp.total_amount) != int(expected):  # >>> CHANGED
        return

    profile = get_user_profile(update.effective_user.id) or {}
    until = compute_expiry(profile, days=30)

    save_user_profile(
        update.effective_user.id,
        premium_activated_at=datetime.now(timezone.utc).isoformat(),  # >>> CHANGED
        premium_until=until.isoformat(),                               # >>> CHANGED
        premium_source="stars",                                        # >>> ADDED
    )

    ui = get_ui_lang(update, ctx)
    msg = (
        f"✅ Оплата прошла! Доступ активен до {until.date().isoformat()}. Приятной практики!"
        if ui == "ru"
        else f"✅ Payment complete! Access active until {until.date().isoformat()}. Enjoy!"
    )
    await update.message.reply_text(msg)
