from __future__ import annotations
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'user_profiles.db'))

def init_usage_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_usage (
          chat_id INTEGER,
          date_utc TEXT,
          used_count INTEGER,
          PRIMARY KEY (chat_id, date_utc)
        )
    """)
    conn.commit()
    conn.close()

def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()

def get_usage(chat_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT used_count FROM user_usage WHERE chat_id=? AND date_utc=?", (chat_id, _today()))
    row = cur.fetchone()
    conn.close()
    return int(row[0]) if row else 0

def increment_usage(chat_id: int) -> int:
    today = _today()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT used_count FROM user_usage WHERE chat_id=? AND date_utc=?", (chat_id, today))
    row = cur.fetchone()
    if row:
        used = int(row[0]) + 1
        cur.execute("UPDATE user_usage SET used_count=? WHERE chat_id=? AND date_utc=?", (used, chat_id, today))
    else:
        used = 1
        cur.execute("INSERT INTO user_usage (chat_id, date_utc, used_count) VALUES (?, ?, ?)", (chat_id, today, used))
    conn.commit()
    conn.close()
    return used
