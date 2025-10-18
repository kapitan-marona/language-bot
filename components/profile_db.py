# components/profile_db.py
from __future__ import annotations
import os
import sqlite3
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone, timedelta

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

    # Автомиграция: добавим колонки под промокоды, напоминания, автоперевод и подписку
    cur.execute("PRAGMA table_info(user_profiles)")
    existing = {row[1] for row in cur.fetchall()}  # имена колонок

    required_cols = {
        # промокоды
        "promo_code_used": "TEXT",        # нормализованный код (строка)
        "promo_type": "TEXT",             # 'timed' | 'permanent' | 'english_only'
        "promo_activated_at": "TEXT",     # ISO-8601 (UTC)
        "promo_days": "INTEGER",          # число дней для timed
        # напоминания
        "last_seen_at": "TEXT",           # ISO-8601 (UTC) — последний визит
        "nudge_last_sent": "TEXT",        # ISO-8601 (UTC) — когда слали напоминание
        # автоперевод
        "append_translation": "INTEGER",  # 0/1
        "append_translation_lang": "TEXT",# код языка интерфейса (ru/en/…)
        # подписка
        "premium_until": "TEXT",          # ISO-8601 (UTC) — до какого момента активна подписка
        "premium_activated_at": "TEXT",   # ISO-8601 (UTC)
        "premium_source": "TEXT",         # payment|promo|gift...
    }
    for col, coltype in required_cols.items():
        if col not in existing:
            cur.execute(f"ALTER TABLE user_profiles ADD COLUMN {col} {coltype}")

    # История сообщений (контекст для восстановления после ребута)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,          -- 'user' | 'assistant' | 'system'
            content TEXT NOT NULL,
            ts TEXT NOT NULL             -- ISO-8601 UTC
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_ts ON messages (chat_id, ts)")

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
    # Напоминания
    last_seen_at: Optional[str] = None,
    nudge_last_sent: Optional[str] = None,
    # Автоперевод
    append_translation: Optional[bool] = None,
    append_translation_lang: Optional[str] = None,
    # Подписка
    premium_until: Optional[str] = None,
    premium_activated_at: Optional[str] = None,
    premium_source: Optional[str] = None,
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
        "append_translation": int(append_translation) if append_translation is not None else current.get("append_translation"),
        "append_translation_lang": append_translation_lang if append_translation_lang is not None else current.get("append_translation_lang"),
        "premium_until": premium_until if premium_until is not None else current.get("premium_until"),
        "premium_activated_at": premium_activated_at if premium_activated_at is not None else current.get("premium_activated_at"),
        "premium_source": premium_source if premium_source is not None else current.get("premium_source"),
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
              last_seen_at = ?, nudge_last_sent = ?,
              append_translation = ?, append_translation_lang = ?,
              premium_until = ?, premium_activated_at = ?, premium_source = ?
            WHERE chat_id = ?
            """,
            (
                updates["name"], updates["interface_lang"], updates["target_lang"],
                updates["level"], updates["style"],
                updates["promo_code_used"], updates["promo_type"],
                updates["promo_activated_at"], updates["promo_days"],
                updates["last_seen_at"], updates["nudge_last_sent"],
                updates["append_translation"], updates["append_translation_lang"],
                updates["premium_until"], updates["premium_activated_at"], updates["premium_source"],
                chat_id,
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO user_profiles (
              chat_id, name, interface_lang, target_lang, level, style,
              promo_code_used, promo_type, promo_activated_at, promo_days,
              last_seen_at, nudge_last_sent,
              append_translation, append_translation_lang,
              premium_until, premium_activated_at, premium_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                updates["name"], updates["interface_lang"], updates["target_lang"],
                updates["level"], updates["style"],
                updates["promo_code_used"], updates["promo_type"],
                updates["promo_activated_at"], updates["promo_days"],
                updates["last_seen_at"], updates["nudge_last_sent"],
                updates["append_translation"], updates["append_translation_lang"],
                updates["premium_until"], updates["premium_activated_at"], updates["premium_source"],
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


# === Подписка (premium) ===

def is_premium(profile: dict) -> bool:
    """Проверяет активна ли подписка по полю premium_until (ISO-8601, UTC)."""
    if not isinstance(profile, dict):
        return False
    until = profile.get("premium_until")
    if not until:
        return False
    try:
        dt = datetime.fromisoformat(str(until).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) <= dt
    except Exception:
        return False


def set_premium_for_days(chat_id: int, days: int, *, source: str = "payment") -> None:
    """Активировать/продлить подписку на days дней от текущего момента."""
    now = datetime.now(timezone.utc)
    save_user_profile(
        chat_id,
        premium_activated_at=now.isoformat(),
        premium_until=(now + timedelta(days=int(days))).isoformat(),
        premium_source=source,
    )


# === История сообщений для восстановления контекста ===

def save_message(chat_id: int, role: str, content: str, ts_iso: Optional[str] = None) -> None:
    """Сохраняет одно сообщение в БД (для восстановления контекста)."""
    if not content:
        return
    ts = ts_iso or datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (chat_id, role, content, ts) VALUES (?, ?, ?, ?)",
        (chat_id, role, content, ts),
    )
    conn.commit()
    conn.close()


def load_last_messages(chat_id: int, limit: int = 30) -> List[Dict[str, Any]]:
    """Возвращает последние N сообщений (список словарей с role/content)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY ts DESC LIMIT ?",
        (chat_id, int(limit)),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return list(reversed(rows))  # в хронологическом порядке


# --- GDPR-like delete: удалить пользователя из всех таблиц этой БД ---
def delete_user(chat_id: int) -> int:
    """
    Удаляет все строки по chat_id/user_id во всех таблицах этой БД.
    Возвращает количество удалённых строк (суммарно).
    Работает с SQLite.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
    except NameError:
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
