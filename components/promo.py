# promo.py
import datetime
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

PROMO_CODES: Dict[str, Dict[str, Any]] = {
    "0917": {"type": "permanent", "days": None},
    "0825": {"type": "timed", "days": 30},
    "друг": {"type": "timed", "days": 3},
    "Друг": {"type": "timed", "days": 3},
    "ДРУГ": {"type": "timed", "days": 3},
    "friend": {"type": "timed", "days": 3},
    "Friend": {"type": "timed", "days": 3},
    "FRIEND": {"type": "timed", "days": 3},
    "western": {"type": "english_only", "days": None},
    "Western": {"type": "english_only", "days": None},
    "WESTERN": {"type": "english_only", "days": None},
}

def check_promo_code(code: str) -> Dict[str, Any] | None:
    code = (code or "").strip()
    promo = PROMO_CODES.get(code)
    logger.debug("check_promo_code: code=%r -> %r", code, promo)
    return promo

def activate_promo(user_profile: Dict[str, Any], code: str) -> Tuple[bool, str]:
    promo = check_promo_code(code)
    if not promo:
        logger.info("Promo invalid: %r", code)
        return False, "invalid"

    if user_profile.get("promo_code_used"):
        logger.info("Promo already used for user: %r", user_profile.get("promo_code_used"))
        return False, "already_used"

    promo_type = promo["type"]
    days = promo.get("days")
    activated_at = datetime.datetime.utcnow().isoformat()

    user_profile["promo_code_used"] = code
    user_profile["promo_type"] = promo_type
    user_profile["promo_activated_at"] = activated_at
    user_profile["promo_days"] = days

    logger.info("Promo activated: code=%r type=%s days=%r", code, promo_type, days)
    return True, promo_type

def is_promo_valid(user_profile: Dict[str, Any]) -> bool:
    promo_type = user_profile.get("promo_type")
    if not promo_type:
        logger.debug("is_promo_valid: no promo_type in profile")
        return False
    if promo_type in ("permanent", "english_only"):
        return True

    activated = user_profile.get("promo_activated_at")
    days = user_profile.get("promo_days")
    if not activated or not days:
        logger.debug("is_promo_valid: missing activated_at/days -> %r / %r", activated, days)
        return False

    try:
        activated_dt = datetime.datetime.fromisoformat(activated)
    except Exception as e:
        logger.warning("is_promo_valid: invalid date format %r (%s)", activated, e)
        return False

    now = datetime.datetime.utcnow()
    delta = now - activated_dt
    valid = delta.days < int(days)
    logger.debug("is_promo_valid: delta_days=%s days_limit=%s -> %s", delta.days, days, valid)
    return valid

def restrict_target_languages_if_needed(user_profile: Dict[str, Any], lang_dict: Dict[str, str]) -> Dict[str, str]:
    if user_profile.get("promo_type") == "english_only":
        filtered = {k: v for k, v in lang_dict.items() if k == "en"}
        logger.debug("restrict_target_languages_if_needed: english_only -> %s", list(filtered.keys()))
        return filtered
    return lang_dict
