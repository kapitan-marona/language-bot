from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import json

from components.profile_db import get_user_profile, is_premium


# --- Access model (agreed) ---
# Stored in user_profiles table:
#   access_plan TEXT
#   access_expires_at TEXT (ISO UTC or NULL)
#   access_lang_policy TEXT   -> 'all' | 'english_only'
#   access_lang_slots INTEGER -> 1|2|999
#   access_active_langs_json TEXT -> JSON list of active target language codes


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(dt: Any) -> Optional[datetime]:
    if not dt:
        return None
    try:
        d = datetime.fromisoformat(str(dt).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return None


def is_access_active(profile: Dict[str, Any]) -> bool:
    """True if user has any active paid access (promo-based or premium subscription)."""
    if not isinstance(profile, dict):
        return False

    # premium subscription (existing logic)
    try:
        if is_premium(profile):
            return True
    except Exception:
        pass

    plan = (profile.get("access_plan") or "").strip().lower()
    if not plan or plan == "free":
        return False

    exp = _parse_iso(profile.get("access_expires_at"))
    if exp is None:
        return True  # permanent
    return _now() <= exp


def has_unlimited_messages(profile: Dict[str, Any]) -> bool:
    """Unlimited messages if premium or any active non-free access."""
    return bool(is_access_active(profile))


def get_lang_policy(profile: Dict[str, Any]) -> str:
    pol = (profile.get("access_lang_policy") or "").strip().lower()
    return pol if pol in ("all", "english_only") else "all"


def get_lang_slots(profile: Dict[str, Any]) -> int:
    try:
        n = int(profile.get("access_lang_slots") or 0)
        return n if n > 0 else 1
    except Exception:
        return 1


def get_active_langs(profile: Dict[str, Any]) -> List[str]:
    raw = profile.get("access_active_langs_json")
    if not raw:
        return []
    try:
        arr = json.loads(raw)
        if isinstance(arr, list):
            out = []
            for x in arr:
                if isinstance(x, str) and x:
                    out.append(x)
            return out
    except Exception:
        return []
    return []


def _normalize_lang(code: str) -> str:
    return (code or "").strip().lower()


def can_use_target_language(profile: Dict[str, Any], lang_code: str) -> Tuple[bool, str]:
    """Checks policy (english_only) and expiry."""
    lc = _normalize_lang(lang_code)
    if not lc:
        return False, "invalid_lang"

    if is_access_active(profile):
        if get_lang_policy(profile) == "english_only" and lc != "en":
            return False, "english_only"
        return True, "ok"

    # free: any language, but only 1 active at a time (handled on set)
    return True, "ok"


def enforce_and_set_active_language(profile: Dict[str, Any], new_lang: str) -> Tuple[bool, str, List[str]]:
    """Updates active language slots in-memory (caller persists to DB).

    Rules:
    - Free: 1 slot, switching overwrites.
    - Friend: 1 slot, switching overwrites, unlimited while active.
    - Western: english_only, only 'en' allowed.
    - Duo: 2 slots; if choosing new language when full -> keep the newest two.
    - All: unlimited slots; we keep last 2 just for UI neatness.
    """
    lc = _normalize_lang(new_lang)
    ok, reason = can_use_target_language(profile, lc)
    if not ok:
        return False, reason, get_active_langs(profile)

    slots = get_lang_slots(profile)
    active = get_active_langs(profile)

    if slots >= 999:
        if lc in active:
            active = [x for x in active if x != lc] + [lc]
        else:
            active = (active + [lc])[-2:]
        return True, "ok", active

    if slots <= 1:
        return True, "ok", [lc]

    # slots == 2
    if lc in active:
        active = [x for x in active if x != lc] + [lc]
        return True, "ok", active

    if len(active) < 2:
        active.append(lc)
        return True, "ok", active

    active = (active + [lc])[-2:]
    return True, "ok", active


def restrict_language_map(profile: Dict[str, Any], lang_map: Dict[str, str]) -> Dict[str, str]:
    """Returns subset of languages allowed by policy."""
    if not isinstance(lang_map, dict) or not isinstance(profile, dict):
        return lang_map

    if get_lang_policy(profile) == "english_only":
        return {"en": lang_map["en"]} if "en" in lang_map else {}

    return lang_map


def ensure_access_defaults(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures default access fields exist in a profile dict (in-memory)."""
    if not isinstance(profile, dict):
        return {}
    if not profile.get("access_plan"):
        profile["access_plan"] = "free"
    if not profile.get("access_lang_policy"):
        profile["access_lang_policy"] = "all"
    if not profile.get("access_lang_slots"):
        profile["access_lang_slots"] = 1
    return profile


def get_profile(user_id: int) -> Dict[str, Any]:
    p = get_user_profile(user_id) or {"chat_id": user_id}
    return ensure_access_defaults(p)


def has_access(user_id: int) -> bool:
    """Backward compatible name: True if user should bypass free daily limit."""
    p = get_profile(user_id)
    return has_unlimited_messages(p)
