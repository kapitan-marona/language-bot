from __future__ import annotations
import json, os

STORE = os.getenv("CONFIG_STORE_PATH", "config_store.json")

def _load() -> dict:
    if not os.path.exists(STORE):
        return {}
    try:
        with open(STORE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def _save(d: dict) -> None:
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STORE)

def get_kv(key: str, default=None):
    return _load().get(key, default)

def set_kv(key: str, value):
    d = _load()
    d[key] = value
    _save(d)
