# components/promo.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

# Список доступных промокодов (ключи — в нижнем регистре)
PROMO_CODES: Dict[str, Dict[str, Any]] = {
    "1709":    {"type": "permanent",    "days": None},
    "друг":    {"type": "timed",        "days": 3},
    "friend":  {"type": "timed",        "days": 3},
    "western": {"type": "english_only", "days": None},
    # 🎓 Frau — до 26.10 включительно, открывает DE/EN
    "frau":    {"type": "timed",        "days": None, "expires_at": "2025-10-26"},
}

# ============== Утилиты промо-логики ==============

def normalize_code(code: str) -> str:
    """Приводим код к единому виду (без регистра и лишних пробелов)."""
    return (code or "").strip().lower()

def _expiry_eod_utc(date_str: str) -> Optional[datetime]:
    """
    Интерпретируем YYYY-MM-DD как 'до конца дня' (23:59:59 UTC).
    Возвращаем aware-дату в UTC.
    """
    try:
        d = datetime.fromisoformat(date_str)  # date-only: 00:00
        # конец дня UTC
        return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)
    except Exception:
        return None

def check_promo_code(code: str, profile: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Проверка наличия промокода в словаре (без учёта регистра) с учётом expires_at.
    Возвращает описание {'type': ..., 'days': ..., ...} либо None.
    (Аргумент profile оставлен для совместимости со старыми вызовами.)
    """
    key = normalize_code(code)
    info = PROMO_CODES.get(key)
    if not info:
        return None

    # Проверка срока действия (если есть expires_at)
    exp = info.get("expires_at")
    if exp:
        exp_eod = _expiry_eod_utc(exp)
        if exp_eod and datetime.now(timezone.utc) > exp_eod:
            return None  # промокод истёк

    return info

def activate_promo(profile: Dict[str, Any], code: str) -> tuple[bool, str]:
    """
    Активирует промокод в профиле-питоновском словаре (НЕ сохраняет в БД).
    Заполняет:
      - promo_code_used, promo_type, promo_activated_at, promo_days
    Возвращает (ok, reason):
      - (True, '<type>') при успехе;
      - (False, 'invalid') если код не найден/истёк;
      - (False, 'already_used') если у пользователя промо уже активирован.
    """
    if not isinstance(profile, dict):
        return False, "invalid"

    # уже был активирован любой промокод — второй раз нельзя
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
    - permanent / english_only — всегда активны.
    - timed — активен по правилу:
        * если у кода задан expires_at — используем его (до конца дня, UTC);
        * иначе используем (activated_at + promo_days).
    """
    if not isinstance(profile, dict):
        return False

    ptype = profile.get("promo_type")
    if not ptype:
        return False

    if ptype in ("permanent", "english_only"):
        return True

    if ptype == "timed":
        # если у активированного кода есть жёсткий дедлайн — приоритет ему
        code = normalize_code(profile.get("promo_code_used") or "")
        info = PROMO_CODES.get(code) or {}
        exp = info.get("expires_at")
        if exp:
            exp_eod = _expiry_eod_utc(exp)
            if exp_eod:
                return datetime.now(timezone.utc) <= exp_eod

        # fallback: обычные "days" от момента активации
        iso = profile.get("promo_activated_at")
        days = profile.get("promo_days")
        if not iso or not days:
            return False
        try:
            activated = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
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
    Ограничиваем доступные языки при активном промо.
    - english_only  → только 'en'
    - frau          → только 'de' и 'en' (если ещё валиден)
    """
    if not isinstance(lang_map, dict) or not isinstance(profile, dict):
        return lang_map

    promo_type = profile.get("promo_type")
    promo_code = normalize_code(profile.get("promo_code_used") or "")

    if promo_type == "english_only" and is_promo_valid(profile):
        return {"en": lang_map["en"]} if "en" in lang_map else {}

    if promo_code == "frau" and is_promo_valid(profile):
        allowed = {"de", "en"}
        return {k: v for k, v in lang_map.items() if k in allowed}

    return lang_map

# ============== UI-статус промокода для /promo ==============

def _days_word_ru(n: int) -> str:
    n = abs(n) % 100
    if 11 <= n <= 14:
        return "дней"
    last = n % 10
    if last == 1:
        return "день"
    if 2 <= last <= 4:
        return "дня"
    return "дней"

def _days_word_en(n: int) -> str:
    return "day" if abs(n) == 1 else "days"

def format_promo_status_for_user(profile: dict, lang: str = "ru") -> str:
    """
    Унифицированное сообщение о статусе промокода.
    Возвращает многострочную строку на ru|en:
      заголовок "Промокод {code}:" / "Promo code {code}:"
      + тело (permanent / english_only / timed / frau / not_active)
    """
    from components.promo_texts import PROMO_HEADER_TPL, PROMO_DETAILS

    lang = "en" if lang == "en" else "ru"

    code_used = normalize_code(profile.get("promo_code_used") or "")
    ptype = (profile.get("promo_type") or "").strip()
    days_total = profile.get("promo_days")
    iso = profile.get("promo_activated_at")

    # не активирован
    if not ptype:
        return PROMO_DETAILS[lang]["not_active"]

    header = PROMO_HEADER_TPL[lang].format(code=code_used or "").strip()

    # frau — показываем фиксированный текст, если ещё не истёк
    if code_used == "frau":
        info = PROMO_CODES.get("frau", {})
        exp = info.get("expires_at")
        exp_eod = _expiry_eod_utc(exp) if exp else None
        if exp_eod and datetime.now(timezone.utc) > exp_eod:
            return PROMO_DETAILS[lang]["not_active"]
        # В PROMO_DETAILS заранее должен быть ключ 'frau' (ru/en) — мы его добавляли раньше
        return f"{header}\n{PROMO_DETAILS[lang]['frau']}"

    # бессрочные
    if ptype == "permanent":
        return f"{header}\n{PROMO_DETAILS[lang]['permanent_all']}"
    if ptype == "english_only":
        return f"{header}\n{PROMO_DETAILS[lang]['english_only']}"

    # ограниченные по времени
    if ptype == "timed":
        # если есть глобальный дедлайн у кода — приоритетно
        info = PROMO_CODES.get(code_used) or {}
        exp = info.get("expires_at")
        exp_eod = _expiry_eod_utc(exp) if exp else None
        if exp_eod:
            now = datetime.now(timezone.utc)
            if now > exp_eod:
                return PROMO_DETAILS[lang]["not_active"]
            # считаем оставшиеся дни до экспирации
            days_left = ((exp_eod - now).total_seconds() + 86399) // 86400
            days_left = int(max(1, days_left))
            dw = _days_word_en(days_left) if lang == "en" else _days_word_ru(days_left)
            body = PROMO_DETAILS[lang]["timed_generic"].format(days=days_left, days_word=dw)
            return f"{header}\n{body}"

        # иначе — классическая модель days от активированного момента
        if not iso or not days_total:
            body = PROMO_DETAILS[lang]["timed_generic"].format(
                days="?", days_word=_days_word_en(2) if lang == "en" else _days_word_ru(2)
            )
            return f"{header}\n{body}"
        try:
            dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            body = PROMO_DETAILS[lang]["timed_generic"].format(
                days="?", days_word=_days_word_en(2) if lang == "en" else _days_word_ru(2)
            )
            return f"{header}\n{body}"

        now = datetime.now(timezone.utc)
        end = dt + timedelta(days=int(days_total))
        left_seconds = int((end - now).total_seconds())
        if left_seconds <= 0:
            return PROMO_DETAILS[lang]["not_active"]

        days_left = (left_seconds + 86399) // 86400  # ceil до дней
        dw = _days_word_en(days_left) if lang == "en" else _days_word_ru(days_left)
        body = PROMO_DETAILS[lang]["timed_generic"].format(days=int(days_left), days_word=dw)
        return f"{header}\n{body}"

    # неизвестный тип
    return f"{header}\n{PROMO_DETAILS[lang]['unknown_type']}"
