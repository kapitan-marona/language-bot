import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'user_profiles.db')
DB_PATH = os.path.abspath(DB_PATH)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            chat_id INTEGER PRIMARY KEY,
            name TEXT,
            interface_lang TEXT,
            target_lang TEXT,
            level TEXT,
            style TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_user_profile(chat_id, name=None, interface_lang=None, target_lang=None, level=None, style=None):
    """Сохраняет или обновляет профиль пользователя."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO user_profiles (chat_id, name, interface_lang, target_lang, level, style)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET
            name=excluded.name,
            interface_lang=excluded.interface_lang,
            target_lang=excluded.target_lang,
            level=excluded.level,
            style=excluded.style
    ''', (chat_id, name, interface_lang, target_lang, level, style))
    conn.commit()
    conn.close()

def get_user_profile(chat_id):
    """Возвращает словарь с профилем пользователя."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT * FROM user_profiles WHERE chat_id=?', (chat_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "chat_id": row[0],
        "name": row[1],
        "interface_lang": row[2],
        "target_lang": row[3],
        "level": row[4],
        "style": row[5],
    }
