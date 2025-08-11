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


def _human_time_left(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    if total_seconds <= 0:
        return "0 дней"
    days = total_seconds // 86400
    if days >= 2:
        return f"{days} {_plural_ru_days(days)}"
    hours = (total_seconds % 86400) // 3600
    if days == 1 and hours > 0:
        return f"1 день {hours} ч"
    if days == 1 and hours == 0:
        return "1 день"
    return f"{max(1, hours)} ч"


def _parse_iso(dt: Optional[str]) -> Optional[datetime]:
    if not dt:
        return None
    try:
        d = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def format_promo_status_for_user(profile: dict) -> str:
    """
    Красивый статус промокода для пользователя (эмодзи + построчно).
    """
    code_used = (profile.get("promo_code_used") or "").strip()
    ptype = (profile.get("promo_type") or "").strip()
    days_total = profile.get("promo_days")
    activated_at = _parse_iso(profile.get("promo_activated_at"))
    now = datetime.now(timezone.utc)

    # Бессрочные
    if ptype in ("permanent", "english_only"):
        if normalize_code(code_used) in ("western",):
            return "♾️ действует бессрочно\n🇬🇧 открывает английский язык"
        else:
            return "❤️ бессрочный\n❤️ действует всегда\n❤️ открывает все языки"

    # Временные
    if ptype == "timed":
        if activated_at and days_total:
            expires = activated_at + timedelta(days=int(days_total))
            left = max(expires - now, timedelta(0))
        else:
            left = timedelta(0)

        norm = normalize_code(code_used)
        if norm in ("friend", "друг"):
            return f"⏳ действует ещё {_human_time_left(left)}\n🌐 открывает все языки и возможности\n🕊️ без ограничений"
        if norm == "0825":
            end_of_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            left_em = max(end_of_month - now, timedelta(0))
            left_days = max(0, int(left_em.total_seconds() // 86400))
            return f"⏳ действует до конца месяца — ещё {left_days} {_plural_ru_days(left_days)}\n🌐 открывает все языки и возможности\n🕊️ без ограничений"

        return f"⏳ действует ещё {_human_time_left(left)}\n🌐 открывает все языки и возможности\n🕊️ без ограничений"

    return "🎟️ промокод не активирован\nℹ️ отправь: /promo <код>"


async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Пользовательская команда:
    - /promo              → показать статус
    - /promo <код>        → активировать код и показать статус
    """
    chat_id = update.effective_chat.id
    args = context.args or []
    code = (args[0] if args else "").strip()

    profile = get_user_profile(chat_id) or {"chat_id": chat_id}

    if code:
        if not check_promo_code(code):
            await update.message.reply_text("❌ неизвестный промокод")
            return
        ok, msg = activate_promo(profile, code)
        if ok:
            save_user_profile(
                chat_id,
                promo_code_used=profile.get("promo_code_used"),
                promo_type=profile.get("promo_type"),
                promo_activated_at=profile.get("promo_activated_at"),
                promo_days=profile.get("promo_days"),
            )
            await update.message.reply_text(format_promo_status_for_user(profile))
            return
        else:
            await update.message.reply_text(msg or "⚠️ не удалось активировать промокод")
            return

    await update.message.reply_text(format_promo_status_for_user(profile))
