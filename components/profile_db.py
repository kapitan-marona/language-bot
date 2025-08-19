from __future__ import annotations
import os
import json
import sqlite3
from typing import Any, Dict, Optional, List

# Абсолютный путь к файлу БД рядом с проектом
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'user_profiles.db'))


def init_db() -> None:
    """
    Инициализация БД и безопасная автомиграция недостающих колонок.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Базовая таблица
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            chat_id INTEGER PRIMARY KEY,
            name TEXT,
            interface_lang TEXT,
            target_lang TEXT,
            level TEXT,
            style TEXT
        )
        """
    )

    # Автомиграция: добавляем недостающие колонки по мере появления фич
    cur.execute("PRAGMA table_info(user_profiles)")
    existing = {row[1] for row in cur.fetchall()}

    required_cols = {
        # промо-столбцы из старых версий
        "promo_code_used": "TEXT",
        "promo_type": "TEXT",
        "promo_activated_at": "TEXT",
        "promo_days": "INTEGER",
        # НОВОЕ: поминутные промо + история использованных кодов
        "promo_minutes": "INTEGER",
        "promo_used_codes": "TEXT",  # JSON-массив строк
        # (если будет премиум — можно добавить premium_expires_at TEXT и т.д.)
    }
    for col, coltype in required_cols.items():
        if col not in existing:
            cur.execute(f"ALTER TABLE user_profiles ADD COLUMN {col} {coltype}")

    conn.commit()
    conn.close()


def _decode_used_codes(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return [str(x) for x in data] if isinstance(data, list) else []
    except Exception:
        return []


def _encode_used_codes(val: Optional[Any]) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, str):
        # уже json
        return val
    if isinstance(val, list):
        return json.dumps([str(x) for x in val], ensure_ascii=False)
    # что-то иное — не сохраняем
    return None


# === Чтение профиля ===

def get_user_profile(chat_id: int) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_profiles WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    # Декодируем JSON-поле истории промокодов
    d["promo_used_codes"] = _decode_used_codes(d.get("promo_used_codes"))
    return d


# === Запись профиля (upsert) ===

def save_user_profile(
    chat_id: int,
    *,
    name: Optional[str] = None,
    interface_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
    level: Optional[str] = None,
    style: Optional[str] = None,
    # промо
    promo_code_used: Optional[str] = None,
    promo_type: Optional[str] = None,
    promo_activated_at: Optional[str] = None,
    promo_days: Optional[int] = None,
    promo_minutes: Optional[int] = None,             # NEW
    promo_used_codes: Optional[Any] = None,          # NEW (list[str] | json str)
) -> None:
    """
    Частичный upsert: обновляет только переданные значения.
    """
    current = get_user_profile(chat_id) or {"chat_id": chat_id}

    updates = {
        "name": name if name is not None else current.get("name"),
        "interface_lang": interface_lang if interface_lang is not None else current.get("interface_lang"),
        "target_lang": target_lang if target_lang is not None else current.get("target_lang"),
        "level": level if level is not None else current.get("level"),
        "style": style if style is not None else current.get("style"),

        "promo_code_used": promo_code_used if promo_code_used is not None else current.get("promo_code_used"),
        "promo_type": promo_type if promo_type is not None else current.get("promo_type"),
        "promo_activated_at": promo_activated_at if promo_activated_at is not None else current.get("promo_activated_at"),
        "promo_days": promo_days if promo_days is not None else current.get("promo_days"),
        "promo_minutes": promo_minutes if promo_minutes is not None else current.get("promo_minutes"),
        # храним как JSON-строку
        "promo_used_codes": _encode_used_codes(promo_used_codes) if promo_used_codes is not None
                            else _encode_used_codes(current.get("promo_used_codes")),
    }

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM user_profiles WHERE chat_id = ?", (chat_id,))
    exists = cur.fetchone() is not None

    if exists:
        cur.execute(
            """
            UPDATE user_profiles SET
              name=?, interface_lang=?, target_lang=?, level=?, style=?,
              promo_code_used=?, promo_type=?, promo_activated_at=?, promo_days=?,
              promo_minutes=?, promo_used_codes=?
            WHERE chat_id=?
            """,
            (
                updates["name"], updates["interface_lang"], updates["target_lang"],
                updates["level"], updates["style"],
                updates["promo_code_used"], updates["promo_type"], updates["promo_activated_at"],
                updates["promo_days"], updates["promo_minutes"], updates["promo_used_codes"],
                chat_id,
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO user_profiles (
              chat_id, name, interface_lang, target_lang, level, style,
              promo_code_used, promo_type, promo_activated_at, promo_days,
              promo_minutes, promo_used_codes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                updates["name"], updates["interface_lang"], updates["target_lang"],
                updates["level"], updates["style"],
                updates["promo_code_used"], updates["promo_type"], updates["promo_activated_at"],
                updates["promo_days"], updates["promo_minutes"], updates["promo_used_codes"],
            ),
        )

    conn.commit()
    conn.close()


# Точечный сеттер промо (если удобнее)
def set_user_promo(
    chat_id: int,
    code: Optional[str],
    promo_type: Optional[str],
    activated_at: Optional[str],
    days: Optional[int],
    minutes: Optional[int] = None,
    used_codes: Optional[List[str]] = None,
) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM user_profiles WHERE chat_id = ?", (chat_id,))
    exists = cur.fetchone() is not None

    used_json = _encode_used_codes(used_codes)

    if exists:
        cur.execute(
            """
            UPDATE user_profiles SET
              promo_code_used=?, promo_type=?, promo_activated_at=?, promo_days=?,
              promo_minutes=?, promo_used_codes=?
            WHERE chat_id=?
            """,
            (code, promo_type, activated_at, days, minutes, used_json, chat_id),
        )
    else:
        cur.execute(
            """
            INSERT INTO user_profiles (
              chat_id, promo_code_used, promo_type, promo_activated_at, promo_days,
              promo_minutes, promo_used_codes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (chat_id, code, promo_type, activated_at, days, minutes, used_json),
        )

    conn.commit()
    conn.close()
