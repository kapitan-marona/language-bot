from __future__ import annotations
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'user_profiles.db'))

def _connect():
    # Надёжные PRAGMA для параллельной нагрузки
    conn = sqlite3.connect(DB_PATH, timeout=5)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("PRAGMA busy_timeout=5000;")
    return conn, cur

def init_usage_db() -> None:
    conn, cur = _connect()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_usage (
              chat_id INTEGER,
              date_utc TEXT,
              used_count INTEGER,
              PRIMARY KEY (chat_id, date_utc)
            )
        """)
        conn.commit()
    finally:
        conn.close()

def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()

def get_usage(chat_id: int) -> int:
    conn, cur = _connect()
    try:
        cur.execute("SELECT used_count FROM user_usage WHERE chat_id=? AND date_utc=?", (chat_id, _today()))
        row = cur.fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()

def increment_usage(chat_id: int) -> int:
    today = _today()
    conn, cur = _connect()
    try:
        # Атомарный UPSERT: если записи нет — будет 1, если есть — инкремент
        cur.execute("""
            INSERT INTO user_usage (chat_id, date_utc, used_count)
            VALUES (?, ?, 1)
            ON CONFLICT(chat_id, date_utc) DO UPDATE SET used_count = user_usage.used_count + 1
        """, (chat_id, today))
        conn.commit()

        cur.execute("SELECT used_count FROM user_usage WHERE chat_id=? AND date_utc=?", (chat_id, today))
        row = cur.fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()

def delete_user(chat_id: int) -> int:
    import sqlite3
    try:
        conn = sqlite3.connect(DB_PATH)
    except NameError:
        raise RuntimeError("DB_PATH is not defined in usage_db.py")

    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cur.fetchall()]

    total = 0
    for t in tables:
        cur.execute(f"PRAGMA table_info({t})")
        cols = [row[1] for row in cur.fetchall()]
        if "chat_id" in cols:
            cur.execute(f"DELETE FROM {t} WHERE chat_id = ?", (chat_id,))
            total += cur.rowcount
        if "user_id" in cols:
            cur.execute(f"DELETE FROM {t} WHERE user_id = ?", (chat_id,))
            total += cur.rowcount

    conn.commit()
    conn.close()
    return total


