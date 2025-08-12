from __future__ import annotations
from datetime import datetime, timezone
from components.profile_db import get_user_profile

def has_access(user_id: int) -> bool:
    p = get_user_profile(user_id)
    if not p:
        return False
    exp = p.get("premium_expires_at")
    if not exp:
        return False
    try:
        return datetime.fromisoformat(exp) > datetime.now(timezone.utc)
    except Exception:
        return False
