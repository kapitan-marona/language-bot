import datetime

# 🔐 Типы поддерживаемых промокодов
PROMO_CODES = {
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


def check_promo_code(code):
    return PROMO_CODES.get(code.strip())


def activate_promo(user_profile, code):
    promo = check_promo_code(code)
    if not promo:
        return False, "invalid"

    if user_profile.get("promo_code_used"):
        return False, "already_used"

    promo_type = promo["type"]
    days = promo.get("days")
    activated_at = datetime.datetime.utcnow().isoformat()

    user_profile["promo_code_used"] = code
    user_profile["promo_type"] = promo_type
    user_profile["promo_activated_at"] = activated_at
    user_profile["promo_days"] = days

    return True, promo_type


def is_promo_valid(user_profile):
    promo_type = user_profile.get("promo_type")
    if not promo_type:
        return False
    if promo_type == "permanent" or promo_type == "english_only":
        return True

    activated = user_profile.get("promo_activated_at")
    days = user_profile.get("promo_days")
    if not activated or not days:
        return False

    activated_dt = datetime.datetime.fromisoformat(activated)
    now = datetime.datetime.utcnow()
    delta = now - activated_dt
    return delta.days < int(days)


def restrict_target_languages_if_needed(user_profile, lang_list):
    if user_profile.get("promo_type") == "english_only":
        return [lang for lang in lang_list if lang[1] == "en"]
    return lang_list
