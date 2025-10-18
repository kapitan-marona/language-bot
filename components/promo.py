from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

# Список доступных промокодов (ключи в нижнем регистре)
PROMO_CODES: Dict[str, Dict[str, Any]] = {
    "1709":   {"type": "permanent",     "days": None},
    "друг":   {"type": "timed",         "days": 3},
    "friend": {"type": "timed",         "days": 3},
    "western":{"type": "english_only",  "days": None},
    # 🎓 Frau — спецкод для студентов школы Deutsch mit Frau Kloppertants
    "frau":   {"type": "timed",         "days": None, "expires_at": "2025-10-26"},
}

def normalize_code(code: str) -> str:
    """Приводим код к единому виду (без учёта регистра и лишних пробелов)."""
    return (code or "").strip().lower()

def check_promo_code(code: str, profile: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Проверка наличия промокода в словаре (без учёта регистра).
    Возвращает описание {'type': ..., 'days': ...} либо None.
    """
    info = PROMO_CODES.get(normalize_code(code))
    if not info:
        return None

    # Проверка срока действия (если есть expires_at)
    exp = info.get("expires_at")
    if exp:
        try:
            exp_date = datetime.fromisoformat(exp).replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp_date:
                return None  # промокод истёк
        except Exception:
            pass

    return info

def activate_promo(profile: Dict[str, Any], code: str) -> tuple[bool, str]:
    """
    Активирует промокод в профиле-питоновском словаре (НЕ сохраняет в БД).
    Возвращает (ok, reason):
      - (True, '<type>') при успехе;
      - (False, 'invalid') если код не найден;
      - (False, 'already_used') если уже активирован ранее;
    """
    if not isinstance(profile, dict):
        return False, "invalid"

    # уже был активирован
    if profile.get("promo_code_used"):
        # если тот же самый — не разрешаем повтор
        if normalize_code(profile["promo_code_used"]) == normalize_code(code):
            return False, "already_used"
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
        if not iso and not days:
            return False

        # если у кода задан expires_at — проверим его
        code = profile.get("promo_code_used")
        info = PROMO_CODES.get(code)
        if info and info.get("expires_at"):
            try:
                exp_date = datetime.fromisoformat(info["expires_at"]).replace(tzinfo=timezone.utc)
                return datetime.now(timezone.utc) <= exp_date
            except Exception:
                pass

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

    return False

def restrict_target_languages_if_needed(profile: Dict[str, Any],
                                        lang_map: Dict[str, str]) -> Dict[str, str]:
    """
    Если активен english_only — оставляем только английский язык из lang_map.
    Если Frau — разрешаем только немецкий и английский.
    """
    if not isinstance(lang_map, dict) or not isinstance(profile, dict):
        return lang_map

    promo_type = profile.get("promo_type")
    promo_code = profile.get("promo_code_used")

    if promo_type == "english_only" and is_promo_valid(profile):
        return {"en": lang_map["en"]} if "en" in lang_map else {}

    if normalize_code(promo_code) == "frau" and is_promo_valid(profile):
        allowed = ["de", "en"]
        return {k: v for k, v in lang_map.items() if k in allowed}

    return lang_map
