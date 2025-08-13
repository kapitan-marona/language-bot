from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from components.profile_db import get_user_profile, save_user_profile
from components.promo import check_promo_code, activate_promo, normalize_code

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

def format_promo_status_for_user(p: dict) -> str:
    activated = p.get("promo_activated_at")
    days = int(p.get("promo_days") or 0)
    if not activated or not days:
        return "Промокод не активирован." if (p.get("interface_lang") or "ru") == "ru" else "Promo code is not activated."
    try:
        dt = datetime.fromisoformat(activated)
    except Exception:
        dt = None
    until = dt + timedelta(days=days) if dt else None
    lang = (p.get("interface_lang") or "ru")
    if lang == "ru":
        return f"🎟 Промо активно: {days} {_plural_ru_days(days)}. Действует до {until.astimezone().strftime('%d.%m.%Y') if until else '—'}."
    else:
        return f"🎟 Promo active: {days} days. Valid until {until.astimezone().strftime('%Y-%m-%d') if until else '—'}."

def _ui_lang(ctx: ContextTypes.DEFAULT_TYPE) -> str:
    return ctx.user_data.get("ui_lang", "ru")

async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /promo              → показать статус
    /promo <код>        → активировать код и показать статус (+ сообщение, что лимит снят)
    """
    chat_id = update.effective_chat.id
    args = context.args or []

    profile = get_user_profile(chat_id) or {}
    ui = _ui_lang(context)

    if not args:
        await update.effective_message.reply_text(format_promo_status_for_user(profile))
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
        await update.effective_message.reply_text(format_promo_status_for_user(profile))
        tail = ("✅ Лимит сообщений снят — можно продолжать!" if ui == "ru"
                else "✅ Message limit removed — you can continue!")
        await update.effective_message.reply_text(tail)
        return
    else:
        await update.effective_message.reply_text(msg or ("⚠️ не удалось активировать промокод" if ui == "ru" else "⚠️ failed to activate promo code"))
        return
