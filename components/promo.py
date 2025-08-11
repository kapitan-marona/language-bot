# components/promo.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

# Список доступных промокодов (ключи в нижнем регистре)
PROMO_CODES: Dict[str, Dict[str, Any]] = {
    "0917":   {"type": "permanent",    "days": None},
    "0825":   {"type": "timed",        "days": 30},
    "друг":   {"type": "timed",        "days": 3},
    "friend": {"type": "timed",        "days": 3},
    "western":{"type": "english_only", "days": None},
}

def normalize_code(code: str) -> str:
    """Приводим код к единому виду (без учёта регистра и лишних пробелов)."""
    return (code or "").strip().lower()

def check_promo_code(code: str) -> Optional[Dict[str, Any]]:
    """
    Проверка наличия промокода в словаре (без учёта регистра).
    Возвращает описание {'type': ..., 'days': ...} либо None.
    """
    return PROMO_CODES.get(normalize_code(code))

def activate_promo(profile: Dict[str, Any], code: str) -> tuple[bool, str]:
    """
    Активирует промокод в профиле-питоновском словаре (НЕ сохраняет в БД).
    Заполняет:
      - promo_code_used         : str (нормализованный код)
      - promo_type              : 'timed' | 'permanent' | 'english_only'
      - promo_activated_at      : str (ISO-8601, UTC)
      - promo_days              : int | None  (для timed)
    Возвращает (ok, reason):
      - (True, '<type>') при успехе;
      - (False, 'invalid') если код не найден;
      - (False, 'already_used') если уже активирован ранее.
    """
    if not isinstance(profile, dict):
        return False, "invalid"

    # уже был активирован
    if profile.get("promo_code_used"):
        return False, "already_used"

    info = check_promo_code(code)
    if not info:
        return False, "invalid"

    promo_type = info.get("type")
    days = info.get("days")

    profile["promo_code_used"] = normalize_code(code)
    profile["promo_type"] = promo_type
    profile["promo_activated_at"] = datetime.now(timezone.utc).isoformat()
    profile["promo_days"] = int(days) if isinstance(days, int) else None

    return True, str(promo_type or "")

def is_promo_valid(profile: Dict[str, Any]) -> bool:
    """
    Проверяет, действует ли промо на текущий момент.
    permanent / english_only — считаем активными без срока.
    timed — активен, если не истёк интервал с момента активации.
    """
    if not isinstance(profile, dict):
        return False

    ptype = profile.get("promo_type")
    if not ptype:
        return False

    if ptype in ("permanent", "english_only"):
        return True

    if ptype == "timed":
        iso = profile.get("promo_activated_at")
        days = profile.get("promo_days")
        if not iso or not days:
            return False
        try:
            activated = datetime.fromisoformat(iso)
            if activated.tzinfo is None:
                activated = activated.replace(tzinfo=timezone.utc)
        except Exception:
            return False
        end = activated + timedelta(days=int(days))
        return datetime.now(timezone.utc) <= end

    # неизвестный тип — считаем невалидным
    return False

def restrict_target_languages_if_needed(profile: Dict[str, Any],
                                        lang_map: Dict[str, str]) -> Dict[str, str]:
    """
    Если активен english_only — оставляем только английский язык из lang_map (если он там есть).
    lang_map: {'en': 'English', 'fr': 'Français', ...}
    Возвращает НОВУЮ мапу.
    """
    if not isinstance(lang_map, dict) or not isinstance(profile, dict):
        return lang_map

    if profile.get("promo_type") == "english_only" and is_promo_valid(profile):
        return {"en": lang_map["en"]} if "en" in lang_map else {}
    return lang_map

# ---------- пользовательский интерфейс промокодов (статус + команда /promo) ----------
from telegram import Update
from telegram.ext import ContextTypes
from components.profile_db import get_user_profile, save_user_profile

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

    # Нет активного промо
    return "🎟️ промокод не активирован\nℹ️ отправь: /promo <код>"

async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /promo            -> показать статус
    /promo <код>      -> активировать код и показать статус
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
