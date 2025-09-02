from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Literal
from telegram import LabeledPrice, Update
from telegram.ext import ContextTypes
from components.profile_db import save_user_profile, get_user_profile
from components.i18n import get_ui_lang  # NEW

# NEW: импорт хелпера стикеров
from handlers.chat.chat_handler import maybe_send_sticker

Product = Literal["pro_30d"]

XTR_CURRENCY = "XTR"  # Stars валюта

def plan_price_xtr(product: Product) -> list[LabeledPrice]:
    if product == "pro_30d":
        return [LabeledPrice(label="30 days", amount=1000)]
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

# ------------------- PRO (покупка) -------------------

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

# ------------------- DONATION (донаты) -------------------

async def send_donation_invoice(update: Update, ctx: ContextTypes.DEFAULT_TYPE, amount: int) -> None:
    """
    Выставляет счёт на произвольную сумму звёздочек.
    payload = "donation:<amount>:<user_id>" — чтобы отличать от покупки.
    """
    ui = get_ui_lang(update, ctx)
    title = "Пожертвование проекту" if ui == "ru" else "Donation to the Project"
    desc = ("Спасибо за поддержку! Это добровольный взнос в звёздах."
            if ui == "ru" else
            "Thank you for your support! This is a voluntary donation in Stars.")
    payload = f"donation:{amount}:{update.effective_user.id}"
    prices = [LabeledPrice(label="Donation", amount=amount)]

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
    sp = update.message.successful_payment
    if not sp:  # защита
        return

    # Идемпотентность: если такой charge уже обрабатывали — выходим
    profile = get_user_profile(update.effective_user.id)
    if profile and profile.get("last_payment_charge_id") == sp.telegram_payment_charge_id:
        return

    payload = sp.invoice_payload or ""

    # --- Донат: просто благодарим, ничего не меняем в доступе ---
    if payload.startswith("donation:"):
        try:
            # payload: "donation:<amount>:<user_id>"
            _, amount_str, _ = payload.split(":", 2)
            amount = int(amount_str)
        except Exception:
            amount = 0
        ui = get_ui_lang(update, ctx)
        msg = (f"🙏 Спасибо за поддержку! Получено {amount}⭐"
               if ui == "ru" else
               f"🙏 Thank you for your support! Received {amount}⭐")
        await update.message.reply_text(msg)
        return

    # --- Покупка тарифа (как было), с базовой валидацией ---
    if not payload.startswith("pro_30d:"):
        return  # неизвестный payload

    # проверим, что чек адресован этому же пользователю
    try:
        _, uid_str = payload.split(":", 1)
        if int(uid_str) != update.effective_user.id:
            return
    except Exception:
        return

    # проверка валюты и суммы
    if sp.currency != XTR_CURRENCY or sp.total_amount != 1000:
        return

    until = compute_expiry(profile, days=30)
    save_user_profile(
        update.effective_user.id,
        is_premium=1,
        premium_expires_at=until.isoformat(),
        last_payment_charge_id=sp.telegram_payment_charge_id,  # ключ идемпотентности
    )
    ui = get_ui_lang(update, ctx)
    msg = (
        f"✅ Оплата прошла! Доступ активен до {until.date().isoformat()}. Приятной практики!"
        if ui == "ru"
        else f"✅ Payment complete! Access active until {until.date().isoformat()}. Enjoy!"
    )
    await update.message.reply_text(msg)
    # NEW: «иногда» — 0.7 по ТЗ
    await maybe_send_sticker(ctx, update.effective_chat.id, "fire", chance=0.7)
