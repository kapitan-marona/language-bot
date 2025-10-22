from __future__ import annotations
import json, os, time
from typing import Dict, Any, List

STORE = os.getenv("PROMO_STORE_PATH", "promo_codes.json")

def _load() -> Dict[str, Any]:
    if not os.path.exists(STORE):
        return {}
    with open(STORE, "r", encoding="utf-8") as f:
        try:
            return json.load(f) or {}
        except Exception:
            return {}

def _save(data: Dict[str, Any]) -> None:
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STORE)

def list_codes() -> List[Dict[str, Any]]:
    d = _load()
    out = []
    for code, info in d.items():
        rec = dict(info)
        rec["code"] = code
        out.append(rec)
    out.sort(key=lambda x: (not x.get("active", True), x["code"]))
    return out

def upsert_code(code: str, type_: str, value: int, expires_at: int | None, langs: list[str], active=True, notes: str=""):
    d = _load()
    d[code] = {
        "type": type_,
        "value": int(value),
        "expires_at": int(expires_at) if expires_at else None,
        "langs": list(langs or []),
        "active": bool(active),
        "notes": notes,
        "updated_at": int(time.time()),
    }
    _save(d)

def delete_code(code: str) -> bool:
    d = _load()
    if code in d:
        d.pop(code)
        _save(d)
        return True
    return False

def get_code(code: str) -> dict | None:
    return _load().get(code)
