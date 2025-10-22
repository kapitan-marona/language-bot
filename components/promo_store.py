# components/promo_store.py
from __future__ import annotations
from components.config_store import get_kv

def get_promo_info(code: str) -> dict | None:
    """
    Возвращает словарь промокода (или None) из config_store по ключу promo:<code>.
    Поля: type, days, messages, date(YYYY-MM-DD|""), limit, used, allowed_langs
    """
    if not code:
        return None
    return get_kv(f"promo:{code.strip().lower()}", None)
