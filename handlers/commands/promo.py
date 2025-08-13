from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from components.profile_db import get_user_profile, save_user_profile
from components.promo import check_promo_code, activate_promo, normalize_code
from components.i18n import get_ui_lang  # NEW

def _plural_ru_days(n: int) -> str:
    n = abs(n)
    if 11 <= (n % 100) <= 14:
        return "дней"
    last = n % 10
    if last == 1:
        return "день"
    if 2 <= last <= 4:
        return "дня"
    return "дней"

def format_promo_status_for_user(p: dict, ui: str | None = None) -> str:  # CHANGED
    """Локализованный статус промо. Предпочитаем текущую UI-локаль, затем профиль."""
    # NEW: предпочитаем явно переданный язык; иначе — из профиля; дефолт — en
    ui = ui or p.get("interface_lang") or p.get("target_lang") or "en"  # NEW

    activated = p.get("promo_activated_at")
    days = int(p.get("promo_days") or 0)
    if not activated or not days:
        return "Промокод не активирован." if ui == "ru" else "Promo code is not activated."
    try:
        dt = datetime.fromisoformat(activated)
        if dt.tzinfo is None:  # NEW: делаем TZ-aware
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        dt = None
    until = dt + timedelta(days=days) if dt else None

    if ui == "ru":
        return f"🎟 Промо активно: {days} {_plural_ru_days(days)}. Действует до {until.astimezone().strftime('%d.%m.%Y') if until else '—'}."
    else:
        return f"🎟 Promo active: {days} days. Valid until {until.astimezone().strftime('%Y-%m-%d') if until else '—'}."

async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /promo              → показать статус
    /promo <код>        → активировать код и показать статус (+ сообщение, что лимит снят)
    """
    chat_id = update.effective_chat.id
    ui = get_ui_lang(update, context)  # NEW
    args = context.args or []

    profile = get_user_profile(chat_id) or {}

    if not args:
        await update.effective_message.reply_text(format_promo_status_for_user(profile, ui))  # CHANGED
        return

    code = normalize_code(" ".join(args))
    ok, msg, info = check_promo_code(code, profile)
    if ok:
        activate_promo(chat_id, info)
        profile = get_user_profile(chat_id) or profile
        save_user_profile(
            chat_id,
            promo_code_used=profile.get("promo_code_used"),
            promo_type=profile.get("promo_type"),
            promo_activated_at=profile.get("promo_activated_at"),
            promo_days=profile.get("promo_days"),
        )
        await update.effective_message.reply_text(format_promo_status_for_user(profile, ui))  # CHANGED
        tail = ("✅ Лимит сообщений снят — можно продолжать!" if ui == "ru"
                else "✅ Message limit removed — you can continue!")
        await update.effective_message.reply_text(tail)
        return
    else:
        # NEW: если внешний валидатор не даёт локализованное msg — используем локализованный фолбэк
        fallback = "⚠️ не удалось активировать промокод" if ui == "ru" else "⚠️ failed to activate promo code"
        await update.effective_message.reply_text(msg or fallback)
        return
