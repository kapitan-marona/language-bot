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
        "promo_code": "TEXT",
        "promo_activated_at": "TEXT",
        "promo_used": "INTEGER DEFAULT 0",
        # напоминания
        "nudge_enabled": "INTEGER DEFAULT 1",
        "nudge_hour_local": "INTEGER DEFAULT 20",
        "tz_offset_min": "INTEGER DEFAULT 0",
        # переводчик
        "translator_on": "INTEGER DEFAULT 0",
        # подписка
        "premium_until": "TEXT",
        "premium_source": "TEXT",
    }

    for col, ddl in required_cols.items():
        if col not in existing:
            cur.execute(f"ALTER TABLE user_profiles ADD COLUMN {col} {ddl}")

    conn.commit()
    conn.close()


def save_user_profile(
    chat_id: int,
    name: Optional[str] = None,
    interface_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
    level: Optional[str] = None,
    style: Optional[str] = None,
    promo_code: Optional[str] = None,
    promo_activated_at: Optional[str] = None,
    promo_used: Optional[int] = None,
    nudge_enabled: Optional[int] = None,
    nudge_hour_local: Optional[int] = None,
    tz_offset_min: Optional[int] = None,
    translator_on: Optional[int] = None,
    premium_until: Optional[str] = None,
    premium_source: Optional[str] = None,
) -> None:
    """Upsert профиля. Обновляет только переданные поля (None не трогает)."""
    init_db()

    fields: Dict[str, Any] = {}
    if name is not None:
        fields["name"] = name
    if interface_lang is not None:
        fields["interface_lang"] = interface_lang
    if target_lang is not None:
        fields["target_lang"] = target_lang
    if level is not None:
        fields["level"] = level
    if style is not None:
        fields["style"] = style
    if promo_code is not None:
        fields["promo_code"] = promo_code
    if promo_activated_at is not None:
        fields["promo_activated_at"] = promo_activated_at
    if promo_used is not None:
        fields["promo_used"] = promo_used
    if nudge_enabled is not None:
        fields["nudge_enabled"] = nudge_enabled
    if nudge_hour_local is not None:
        fields["nudge_hour_local"] = nudge_hour_local
    if tz_offset_min is not None:
        fields["tz_offset_min"] = tz_offset_min
    if translator_on is not None:
        fields["translator_on"] = translator_on
    if premium_until is not None:
        fields["premium_until"] = premium_until
    if premium_source is not None:
        fields["premium_source"] = premium_source

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ensure row exists
    cur.execute("INSERT OR IGNORE INTO user_profiles (chat_id) VALUES (?)", (chat_id,))

    if fields:
        sets = ", ".join([f"{k}=?" for k in fields.keys()])
        values = list(fields.values())
        values.append(chat_id)
        cur.execute(f"UPDATE user_profiles SET {sets} WHERE chat_id=?", values)

    conn.commit()
    conn.close()


def get_user_profile(chat_id: int) -> Dict[str, Any]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_profiles WHERE chat_id=?", (chat_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else {}


def set_premium(chat_id: int, days: int, source: str = "stars") -> None:
    """Продлить/установить premium на N дней от текущего момента (UTC)."""
    profile = get_user_profile(chat_id)
    now = datetime.now(timezone.utc)

    current_until = None
    if profile.get("premium_until"):
        try:
            current_until = datetime.fromisoformat(profile["premium_until"])
        except Exception:
            current_until = None

    base = current_until if current_until and current_until > now else now
    new_until = base + timedelta(days=int(days))

    save_user_profile(
        chat_id,
        premium_until=new_until.replace(microsecond=0).isoformat(),
        premium_source=source,
    )


def is_premium(chat_id: int) -> bool:
    profile = get_user_profile(chat_id)
    until = profile.get("premium_until")
    if not until:
        return False
    try:
        dt = datetime.fromisoformat(until)
    except Exception:
        return False
    return dt >= datetime.now(timezone.utc)


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


# --- Broadcast audience helpers ---

def get_chat_ids_by_interface_lang(interface_lang: str) -> List[int]:
    """
    Возвращает chat_id пользователей с заданным языком интерфейса (например 'ru' или 'en').
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT DISTINCT chat_id FROM user_profiles WHERE interface_lang=? AND chat_id IS NOT NULL",
            (interface_lang,),
        )
        rows = cur.fetchall()
        return [int(r[0]) for r in rows if r and r[0] is not None]
    finally:
        conn.close()


def get_chat_ids_active_last_days(days: int = 7) -> List[int]:
    """
    Активные пользователи за последние N дней по таблице user_usage
    (used_count > 0 хотя бы в один из дней).
    """
    days = int(days) if days else 7
    if days < 1:
        days = 1

    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=days - 1)).isoformat()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT DISTINCT chat_id
            FROM user_usage
            WHERE date_utc >= ? AND used_count > 0
            """,
            (cutoff,),
        )
        rows = cur.fetchall()
        return [int(r[0]) for r in rows if r and r[0] is not None]
    except sqlite3.OperationalError:
        # таблицы user_usage может не быть на старых инстансах
        return []
    finally:
        conn.close()


def get_chat_ids_active_last_days_by_interface_lang(days: int = 7, interface_lang: str = "en") -> List[int]:
    """
    Активные за N дней + язык интерфейса (join user_profiles + user_usage).
    """
    days = int(days) if days else 7
    if days < 1:
        days = 1

    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=days - 1)).isoformat()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT DISTINCT up.chat_id
            FROM user_profiles up
            JOIN user_usage uu ON uu.chat_id = up.chat_id
            WHERE up.interface_lang = ?
              AND uu.date_utc >= ?
              AND uu.used_count > 0
            """,
            (interface_lang, cutoff),
        )
        rows = cur.fetchall()
        return [int(r[0]) for r in rows if r and r[0] is not None]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()
