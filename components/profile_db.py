import sqlite3
import os

DB_PATH = '/tmp/user_profiles.db'

try:
    with open("/tmp/testfile.txt", "w") as f:
        f.write("ok")
    print("Файл успешно создан в /tmp/")
except Exception as e:
    print("Ошибка создания файла:", e)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            chat_id INTEGER PRIMARY KEY,
            gender TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def save_user_gender(chat_id, gender):
    print(f"[SAVE] chat_id={chat_id}, gender={gender}, DB_PATH={DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO user_profiles (chat_id, gender)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET gender=excluded.gender
    ''', (chat_id, gender))
    conn.commit()
    conn.close()

def get_user_gender(chat_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT gender FROM user_profiles WHERE chat_id=?', (chat_id,))
    row = cur.fetchone()
    conn.close()
    print(f"[GET] chat_id={chat_id}, result={row}, DB_PATH={DB_PATH}")
    return row[0] if row else None

# Важно! Вызови init_db() ОДИН раз при старте бота (например, в точке входа, до запуска polling/webhook)
