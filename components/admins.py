# components/admins.py
from __future__ import annotations
import os

def _parse_admin_ids(raw: str | None) -> set[int]:
    if not raw:
        return set()
    ids: set[int] = set()
    for chunk in raw.replace(",", " ").split():
        if chunk.strip().isdigit():
            ids.add(int(chunk.strip()))
    return ids

# Пример: ADMIN_IDS="123456, 999000"
ADMIN_IDS: set[int] = _parse_admin_ids(os.getenv("ADMIN_IDS"))
