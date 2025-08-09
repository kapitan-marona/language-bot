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
