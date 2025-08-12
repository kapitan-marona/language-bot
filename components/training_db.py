from __future__ import annotations
import os, sqlite3
from typing import List, Tuple

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'user_profiles.db'))

def init_training_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_training_consent (
          chat_id INTEGER PRIMARY KEY,
          consent INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_glossary (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          chat_id INTEGER,
          src_lang TEXT,
          dst_lang TEXT,
          phrase TEXT,
          correction TEXT
        )
    """)
    conn.commit()
    conn.close()

def set_consent(chat_id: int, consent: bool) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO user_training_consent (chat_id, consent) VALUES (?, ?) "
        "ON CONFLICT(chat_id) DO UPDATE SET consent=excluded.consent",
        (chat_id, 1 if consent else 0),
    )
    conn.commit()
    conn.close()

def has_consent(chat_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT consent FROM user_training_consent WHERE chat_id=?", (chat_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row and row[0])

def add_glossary(chat_id: int, src_lang: str, dst_lang: str, phrase: str, correction: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO user_glossary (chat_id, src_lang, dst_lang, phrase, correction) "
        "VALUES (?, ?, ?, ?, ?)",
        (chat_id, src_lang.strip(), dst_lang.strip(), phrase.strip(), correction.strip()),
    )
    conn.commit()
    conn.close()

def get_glossary(chat_id: int) -> List[Tuple[str, str, str, str]]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT src_lang, dst_lang, phrase, correction FROM user_glossary WHERE chat_id=?",
        (chat_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [(r[0], r[1], r[2], r[3]) for r in rows]
