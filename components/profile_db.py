from __future__ import annotations
import os
import sqlite3
from typing import Any, Dict, Optional, List

# Абсолютный путь к файлу БД рядом с проектом
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'user_profiles.db'))


def init_db() -> None:
    """Инициализация БД и безопасная авто-миграция недостающих колонок.

    Таблица user_profiles может уже существовать у старых пользователей —
    добавляем недостающие поля через PRAGMA table_info + ALTER TABLE.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Базовая схема (как было изначально)
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

    # Автомиграция: добавим колонки под промокоды и напоминания, если их ещё нет
    cur.execute("PRAGMA table_info(user_profiles)")
    existing = {row[1] for row in cur.fetchall()}  # имена колонок

    required_cols = {
        "promo_code_used": "TEXT",        # нормализованный код (строка)
        "promo_type": "TEXT",             # 'timed' | 'permanent' | 'english_only'
        "promo_activated_at": "TEXT",     # ISO-8601 (UTC)
        "promo_days": "INTEGER",          # число дней для timed
        # NEW: поля для напоминаний
        "last_seen_at": "TEXT",           # ISO-8601 (UTC) — последний визит
        "nudge_last_sent": "TEXT",        # ISO-8601 (UTC) — когда слали напоминание
    }
    for col, coltype in required_cols.items():
        if col not in existing:
            cur.execute(f"ALTER TABLE user_profiles ADD COLUMN {col} {coltype}")

    conn.commit()
    conn.close()


# === Утилиты чтения/записи профиля ===

def get_user_profile(chat_id: int) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_profiles WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def save_user_profile(
    chat_id: int,
    *,
    name: Optional[str] = None,
    interface_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
    level: Optional[str] = None,
    style: Optional[str] = None,
    # Поля промо
    promo_code_used: Optional[str] = None,
    promo_type: Optional[str] = None,
    promo_activated_at: Optional[str] = None,
    promo_days: Optional[int] = None,
    # NEW: поля для напоминаний
    last_seen_at: Optional[str] = None,
    nudge_last_sent: Optional[str] = None,
) -> None:
    """Обновляет/создаёт профиль пользователя частично (upsert)."""
    current = get_user_profile(chat_id) or {"chat_id": chat_id}

    # Обновляем только переданные значения (не None)
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
        "last_seen_at": last_seen_at if last_seen_at is not None else current.get("last_seen_at"),
        "nudge_last_sent": nudge_last_sent if nudge_last_sent is not None else current.get("nudge_last_sent"),
    }

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # если запись уже есть — UPDATE, иначе INSERT
    cur.execute("SELECT 1 FROM user_profiles WHERE chat_id = ?", (chat_id,))
    exists = cur.fetchone() is not None

    if exists:
        cur.execute(
            """
            UPDATE user_profiles SET
              name = ?, interface_lang = ?, target_lang = ?, level = ?, style = ?,
              promo_code_used = ?, promo_type = ?, promo_activated_at = ?, promo_days = ?,
              last_seen_at = ?, nudge_last_sent = ?
            WHERE chat_id = ?
            """,
            (
                updates["name"], updates["interface_lang"], updates["target_lang"],
                updates["level"], updates["style"],
                updates["promo_code_used"], updates["promo_type"],
                updates["promo_activated_at"], updates["promo_days"],
                updates["last_seen_at"], updates["nudge_last_sent"],
                chat_id,
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO user_profiles (
              chat_id, name, interface_lang, target_lang, level, style,
              promo_code_used, promo_type, promo_activated_at, promo_days,
              last_seen_at, nudge_last_sent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                updates["name"], updates["interface_lang"], updates["target_lang"],
                updates["level"], updates["style"],
                updates["promo_code_used"], updates["promo_type"],
                updates["promo_activated_at"], updates["promo_days"],
                updates["last_seen_at"], updates["nudge_last_sent"],
            ),
        )

    conn.commit()
    conn.close()


# === Новый явный сеттер для промо ===

def set_user_promo(
    chat_id: int,
    code: Optional[str],
    promo_type: Optional[str],
    activated_at: Optional[str],
    days: Optional[int],
) -> None:
    """Сохраняет только поля промокода для пользователя (upsert)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM user_profiles WHERE chat_id = ?", (chat_id,))
    exists = cur.fetchone() is not None

    if exists:
        cur.execute(
            """
            UPDATE user_profiles SET
              promo_code_used = ?, promo_type = ?, promo_activated_at = ?, promo_days = ?
            WHERE chat_id = ?
            """,
            (code, promo_type, activated_at, days, chat_id),
        )
    else:
        cur.execute(
            """
            INSERT INTO user_profiles (
              chat_id, promo_code_used, promo_type, promo_activated_at, promo_days
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (chat_id, code, promo_type, activated_at, days),
        )

    conn.commit()
    conn.close()


# --- GDPR-like delete: удалить пользователя из всех таблиц этой БД ---
def delete_user(chat_id: int) -> int:
    """
    Удаляет все строки по chat_id/user_id во всех таблицах этой БД.
    Возвращает количество удалённых строк (суммарно).
    Работает с SQLite.
    """
    import sqlite3
    try:
        conn = sqlite3.connect(DB_PATH)  # предполагаем, что DB_PATH уже есть в модуле
    except NameError:
        # Если у вас другая переменная, поправьте строку выше.
        raise RuntimeError("DB_PATH is not defined in profile_db.py")

    cur = conn.cursor()
    # список таблиц (кроме служебных)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cur.fetchall()]

    total = 0
    for t in tables:
        # смотрим, какие колонки есть
        cur.execute(f"PRAGMA table_info({t})")
        cols = [row[1] for row in cur.fetchall()]
        # пробуем удалить по chat_id или user_id
        if "chat_id" in cols:
            cur.execute(f"DELETE FROM {t} WHERE chat_id = ?", (chat_id,))
            total += cur.rowcount
        if "user_id" in cols:
            cur.execute(f"DELETE FROM {t} WHERE user_id = ?", (chat_id,))
            total += cur.rowcount

    conn.commit()
    conn.close()
    return total


# NEW: список всех chat_id для рассылки напоминаний
def get_all_chat_ids() -> List[int]:
    """
    Возвращает список chat_id, у кого есть профиль.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT chat_id FROM user_profiles WHERE chat_id IS NOT NULL")
        rows = cur.fetchall()
        return [int(r[0]) for r in rows if r and r[0] is not None]
    finally:
        conn.close()
