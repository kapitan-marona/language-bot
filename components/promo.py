import datetime

PROMO_CODES = {
    "0917": {"type": "permanent", "days": None},
    "0825": {"type": "timed", "days": 30},
    "друг": {"type": "timed", "days": 3},
    "Western": {"type": "english_only", "days": None},
    "WESTERN": {"type": "english_only", "days": None},
    "western": {"type": "english_only", "days": None},
 
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

def restrict_target_languages_if_needed(user_profile, lang_dict):
    if user_profile.get("promo_type") == "english_only":
        return {k: v for k, v in lang_dict.items() if k == "en"}
    return lang_dict
