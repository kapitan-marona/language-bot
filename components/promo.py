# components/promo.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import json

from components.promo_db import get_code as _db_get_code, redeem as _db_redeem


# Legacy встроенные коды (оставляем для совместимости / временных акций).
# ВАЖНО: основной источник промокодов теперь SQLite (promo_codes).
PROMO_CODES: Dict[str, Dict[str, Any]] = {
    # 🎓 Frau — до 26.10 включительно, открывает DE/EN (legacy)
    "frau":    {"type": "timed", "days": None, "expires_at": "2025-10-26"},
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
        return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)
    except Exception:
        return None


def _info_from_db(code: str) -> Optional[Dict[str, Any]]:
    rec = _db_get_code(code)
    if not rec:
        return None
    if not int(rec.get("active") or 0):
        return None

    days = rec.get("days")
    try:
        days_int = int(days) if days is not None else None
    except Exception:
        days_int = None

    pol = (rec.get("lang_policy") or "all").strip().lower()
    slots = rec.get("lang_slots")
    try:
        slots_int = int(slots) if slots is not None else 1
    except Exception:
        slots_int = 1

    kind = (rec.get("kind") or "").strip()

    if pol == "english_only":
        promo_type = "english_only"
    elif days_int is not None:
        promo_type = "timed"
    else:
        promo_type = "permanent"

    return {
        "type": promo_type,
        "days": days_int,
        "kind": kind,
        "lang_policy": pol,
        "lang_slots": slots_int,
        "is_single_use": int(rec.get("is_single_use") or 0),
    }


def check_promo_code(code: str, profile: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Проверка промокода:
    1) SQLite promo_codes
    2) legacy PROMO_CODES (например, временная акция)
    Возвращает описание {'type': ..., 'days': ..., ...} либо None.
    (Аргумент profile оставлен для совместимости со старыми вызовами.)
    """
    key = normalize_code(code)

    info = _info_from_db(key)
    if info:
        return info

    # legacy fallback
    info = PROMO_CODES.get(key)
    if not info:
        return None

    exp = info.get("expires_at")
    if exp:
        exp_eod = _expiry_eod_utc(exp)
        if exp_eod and datetime.now(timezone.utc) > exp_eod:
            return None

    return info


def _extend_from(current_iso: Optional[str], add_days: int) -> str:
    now = datetime.now(timezone.utc)
    base = now
    if current_iso:
        try:
            cur = datetime.fromisoformat(str(current_iso).replace("Z", "+00:00"))
            if cur.tzinfo is None:
                cur = cur.replace(tzinfo=timezone.utc)
            if cur > base:
                base = cur
        except Exception:
            pass
    return (base + timedelta(days=int(add_days))).isoformat()


def activate_promo(profile: Dict[str, Any], code: str) -> tuple[bool, str]:
    """
    Активирует промокод в профиле-питоновском словаре (НЕ сохраняет в БД).
    Новая логика (по договорённости):
      - промокоды берём из SQLite promo_codes
      - поддерживаем одноразовые коды (friend/друг)
      - WESTERN многоразовый, English-only
      - 1709 многоразовый, All без срока
    Для совместимости продолжает заполнять promo_* поля.
    """
    if not isinstance(profile, dict):
        return False, "invalid"

    key = normalize_code(code)
    info = check_promo_code(key)
    if not info:
        return False, "invalid"

    # Если это DB-код — применяем правила одноразовости через redeem()
    if info.get("kind") and key not in PROMO_CODES:
        ok, reason, _ = _db_redeem(key, int(profile.get("chat_id") or 0))
        if not ok:
            return False, reason

    promo_type = info.get("type")
    days = info.get("days")

    # --- legacy promo fields (для /promo статуса и старых частей кода) ---
    profile["promo_code_used"] = key
    profile["promo_type"] = promo_type
    profile["promo_activated_at"] = datetime.now(timezone.utc).isoformat()
    profile["promo_days"] = int(days) if isinstance(days, int) else None

    # --- New access fields (agreed) ---
    lang_policy = (info.get("lang_policy") or "all").strip().lower()
    try:
        lang_slots = int(info.get("lang_slots") or 1)
    except Exception:
        lang_slots = 1

    # plan name is used only for logic; keep simple & explicit
    if lang_policy == "english_only":
        # WESTERN
        plan = "western"
        expires_at = None
        lang_slots = 1
        active_langs = ["en"]
    else:
        # Timed or permanent plans depend on slots:
        #   slots==1  -> friend (shareable 3d) or other 1-slot promos
        #   slots==2  -> duo
        #   slots>=999 -> all
        if isinstance(days, int):
            if int(lang_slots) >= 999:
                plan = "all"
                expires_at = _extend_from(profile.get("access_expires_at"), int(days))
            elif int(lang_slots) == 2:
                plan = "duo"
                expires_at = _extend_from(profile.get("access_expires_at"), int(days))
            else:
                plan = "friend"
                # friend is per-user-once, but keep consistent extension rule
                expires_at = _extend_from(profile.get("access_expires_at"), int(days))
            active_langs = []
        else:
            # Permanent (e.g., 1709)
            if int(lang_slots) >= 999:
                plan = "all"
            elif int(lang_slots) == 2:
                plan = "duo"
            else:
                plan = "premium"
            expires_at = None
            active_langs = []

    profile["access_plan"] = plan

    profile["access_expires_at"] = expires_at
    profile["access_lang_policy"] = lang_policy
    profile["access_lang_slots"] = int(lang_slots)

    # active languages: keep existing if valid, otherwise set by target_lang
    try:
        existing = json.loads(profile.get("access_active_langs_json") or "[]")
        if not isinstance(existing, list):
            existing = []
    except Exception:
        existing = []

    if not active_langs:
        tl = (profile.get("target_lang") or "en").strip().lower()
        if lang_policy == "english_only":
            active_langs = ["en"]
        else:
            if int(lang_slots) <= 1:
                active_langs = [tl]
            else:
                merged = [x for x in existing if isinstance(x, str)]
                if tl and tl not in merged:
                    merged.append(tl)
                active_langs = merged[-int(lang_slots):] if merged else [tl]

    profile["access_active_langs_json"] = json.dumps(active_langs, ensure_ascii=False)

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
        code = normalize_code(profile.get("promo_code_used") or "")
        info = PROMO_CODES.get(code) or {}
        exp = info.get("expires_at")
        if exp:
            exp_eod = _expiry_eod_utc(exp)
            if exp_eod:
                return datetime.now(timezone.utc) <= exp_eod

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

    return False


def restrict_target_languages_if_needed(profile: Dict[str, Any],
                                        lang_map: Dict[str, str]) -> Dict[str, str]:
    """
    Ограничиваем доступные языки при активном доступе.
    - WESTERN (english_only) → только 'en'
    - legacy 'frau'          → только 'de' и 'en' (если ещё валиден)
    """
    if not isinstance(lang_map, dict) or not isinstance(profile, dict):
        return lang_map

    if (profile.get("access_lang_policy") == "english_only"):
        return {"en": lang_map["en"]} if "en" in lang_map else {}

    promo_code = normalize_code(profile.get("promo_code_used") or "")
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
    """Оставляем прежний формат статуса /promo, но учитываем новые access_* поля."""
    from components.promo_texts import PROMO_HEADER_TPL, PROMO_DETAILS

    lang = "en" if lang == "en" else "ru"

    code_used = normalize_code(profile.get("promo_code_used") or "")
    ptype = (profile.get("promo_type") or "").strip()
    iso = profile.get("promo_activated_at")

    if not ptype:
        return PROMO_DETAILS[lang]["not_active"]

    header = PROMO_HEADER_TPL[lang].format(code=code_used or "").strip()

    if code_used == "frau":
        info = PROMO_CODES.get("frau", {})
        exp = info.get("expires_at")
        exp_eod = _expiry_eod_utc(exp) if exp else None
        if exp_eod and datetime.now(timezone.utc) > exp_eod:
            return PROMO_DETAILS[lang]["not_active"]
        return f"{header}\n{PROMO_DETAILS[lang]['frau']}"

    if ptype == "permanent":
        return f"{header}\n{PROMO_DETAILS[lang]['permanent_all']}"
    if ptype == "english_only":
        return f"{header}\n{PROMO_DETAILS[lang]['english_only']}"

    if ptype == "timed":
        exp_iso = profile.get("access_expires_at")
        exp_dt = None
        if exp_iso:
            try:
                exp_dt = datetime.fromisoformat(str(exp_iso).replace("Z", "+00:00"))
                if exp_dt.tzinfo is None:
                    exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            except Exception:
                exp_dt = None

        if exp_dt:
            now = datetime.now(timezone.utc)
            if now > exp_dt:
                return PROMO_DETAILS[lang]["not_active"]
            days_left = ((exp_dt - now).total_seconds() + 86399) // 86400
            days_left = int(max(1, days_left))
            dw = _days_word_en(days_left) if lang == "en" else _days_word_ru(days_left)
            body = PROMO_DETAILS[lang]["timed_generic"].format(days=days_left, days_word=dw)
            return f"{header}\n{body}"

        # fallback: old logic
        days_total = profile.get("promo_days")
        if not iso or not days_total:
            return PROMO_DETAILS[lang]["timed_unknown"]
        try:
            activated = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
            if activated.tzinfo is None:
                activated = activated.replace(tzinfo=timezone.utc)
            end = activated + timedelta(days=int(days_total))
            now = datetime.now(timezone.utc)
            if now > end:
                return PROMO_DETAILS[lang]["not_active"]
            days_left = ((end - now).total_seconds() + 86399) // 86400
            days_left = int(max(1, days_left))
            dw = _days_word_en(days_left) if lang == "en" else _days_word_ru(days_left)
            body = PROMO_DETAILS[lang]["timed_generic"].format(days=days_left, days_word=dw)
            return f"{header}\n{body}"
        except Exception:
            return PROMO_DETAILS[lang]["timed_unknown"]

    return PROMO_DETAILS[lang]["not_active"]
