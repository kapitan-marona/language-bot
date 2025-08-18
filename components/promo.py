# components/promo.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

# ---------- БАЗА КОДОВ ----------
PROMO_CODES: Dict[str, Dict[str, Any]] = {
    "0917":    {"type": "permanent"},                  # навсегда
    "0825":    {"type": "timed", "days": 30},          # 30 дней
    "друг":    {"type": "timed", "days": 3},
    "friend":  {"type": "timed", "days": 3},
    "western": {"type": "english_only"},               # только английский, бессрочно
    "test5m":  {"type": "timed", "minutes": 5},        # ТЕСТОВЫЙ: 5 минут
}

def normalize_code(code: str) -> str:
    return (code or "").strip().lower()

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

# ---------- ПУБЛИЧНЫЕ ФУНКЦИИ ДЛЯ ЛОГИКИ ПРОМО ----------
def check_promo_code(code: str, profile: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Совместимость: второй аргумент (profile) допускается и игнорируется,
    чтобы старые вызовы check_promo_code(code, profile) не падали.
    """
    return PROMO_CODES.get(normalize_code(code))

def _promo_end_from_fields(activated_iso: Optional[str],
                           days: Optional[int],
                           minutes: Optional[int]) -> Optional[datetime]:
    if not activated_iso:
        return None
    try:
        dt = datetime.fromisoformat(str(activated_iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None
    end = dt
    if isinstance(days, int) and days > 0:
        end = end + timedelta(days=days)
    if isinstance(minutes, int) and minutes > 0:
        end = end + timedelta(minutes=minutes)
    return end

def is_promo_valid(profile: Dict[str, Any]) -> bool:
    """permanent/english_only — всегда активен; timed — до наступления конца (по дням/минутам)."""
    if not isinstance(profile, dict):
        return False
    ptype = profile.get("promo_type")
    if not ptype:
        return False
    if ptype in ("permanent", "english_only"):
        return True
    if ptype == "timed":
        end = _promo_end_from_fields(
            profile.get("promo_activated_at"),
            profile.get("promo_days"),
            profile.get("promo_minutes"),
        )
        return bool(end and _now_utc() <= end)
    return False

def activate_promo(profile: Dict[str, Any], code: str) -> tuple[bool, str]:
    """
    Активирует промокод в profile (НЕ сохраняет в БД).
    - Запрещаем повторное применение того же кода в рамках текущего профиля (promo_used_codes).
    - Разрешаем другой код, даже если предыдущий истёк.
    """
    if not isinstance(profile, dict):
        return False, "invalid"

    norm = normalize_code(code)
    info = check_promo_code(norm)
    if not info:
        return False, "invalid"

    used_list = list(profile.get("promo_used_codes") or [])
    if norm in used_list:
        return False, "already_used"

    profile["promo_code_used"] = norm
    profile["promo_type"] = info.get("type")
    profile["promo_activated_at"] = _now_utc().isoformat()
    profile["promo_days"] = int(info["days"]) if isinstance(info.get("days"), int) else None
    profile["promo_minutes"] = int(info["minutes"]) if isinstance(info.get("minutes"), int) else None

    used_list.append(norm)
    profile["promo_used_codes"] = used_list
    return True, str(profile.get("promo_type") or "")

# ---------- ОГРАНИЧЕНИЕ ЯЗЫКОВ ----------
def restrict_target_languages_if_needed(profile: Dict[str, Any], lang_map: Dict[str, str]) -> Dict[str, str]:
    if not isinstance(profile, dict) or not isinstance(lang_map, dict):
        return lang_map
    if profile.get("promo_type") == "english_only" and is_promo_valid(profile):
        return {"en": lang_map["en"]} if "en" in lang_map else {}
    return lang_map

# ---------- UI-СТАТУС ----------
def _days_word_ru(n: int) -> str:
    n = abs(n) % 100
    if 11 <= n <= 14: return "дней"
    last = n % 10
    if last == 1: return "день"
    if 2 <= last <= 4: return "дня"
    return "дней"

def format_promo_status_for_user(profile: dict, lang: str = "ru") -> str:
    lang = "en" if lang == "en" else "ru"
    code = (profile.get("promo_code_used") or "").strip()
    ptype = (profile.get("promo_type") or "").strip()
    if not ptype:
        return "Промокод не активирован." if lang == "ru" else "Promo code is not activated."

    if ptype in ("permanent", "english_only"):
        body = "Бессрочно." if lang == "ru" else "No expiry."
        if ptype == "english_only":
            body = ("Бессрочно. Доступен только английский язык." if lang == "ru"
                    else "No expiry. English only.")
        head = "🎟 Промокод:" if lang == "ru" else "🎟 Promo code:"
        return f"{head} {code}\n{body}"

    if ptype == "timed":
        end = _promo_end_from_fields(
            profile.get("promo_activated_at"),
            profile.get("promo_days"),
            profile.get("promo_minutes"),
        )
        if not end:
            return "Промокод активен (временный)." if lang == "ru" else "Promo active (timed)."
        now = _now_utc()
        if end <= now:
            return "Срок промокода истёк." if lang == "ru" else "Promo has expired."
        left = end - now
        days = int((left.total_seconds() + 86399) // 86400)
        if days >= 1:
            s = f"{days} {_days_word_ru(days)}" if lang == "ru" else f"{days} day(s)"
        else:
            mins = max(1, int(left.total_seconds() // 60))
            s = f"{mins} мин" if lang == "ru" else f"{mins} min"
        head = "🎟 Промокод:" if lang == "ru" else "🎟 Promo code:"
        tail = "Действует ещё " if lang == "ru" else "Valid for another "
        return f"{head} {code}\n{tail}{s}."

    return "Статус промокода неопределён." if lang == "ru" else "Unknown promo status."
