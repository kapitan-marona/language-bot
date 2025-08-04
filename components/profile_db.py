import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.abspath("user_profiles.db")


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                native_lang TEXT,
                target_lang TEXT,
                style TEXT,
                gender TEXT,
                promo_code_used TEXT,                  -- 🟡 добавлено: промокод
                promo_type TEXT,                       -- 🟡 добавлено: тип промо (permanent, timed, english_only)
                promo_activated_at TEXT,               -- 🟡 добавлено: дата активации
                promo_days INTEGER                     -- 🟡 добавлено: сколько дней действует
            )
        ''')
        conn.commit()


def save_user_profile(user_id, profile):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO user_profiles (
                user_id, native_lang, target_lang, style, gender,
                promo_code_used, promo_type, promo_activated_at, promo_days
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            profile.get("native_lang"),
            profile.get("target_lang"),
            profile.get("style"),
            profile.get("gender"),
            profile.get("promo_code_used"),      # 🟡 сохраняем код
            profile.get("promo_type"),           # 🟡 сохраняем тип
            profile.get("promo_activated_at"),   # 🟡 сохраняем дату
            profile.get("promo_days")            # 🟡 сохраняем срок
        ))
        conn.commit()


def load_user_profile(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, native_lang, target_lang, style, gender,
                   promo_code_used, promo_type, promo_activated_at, promo_days
            FROM user_profiles WHERE user_id = ?
        ''', (user_id,))
        row = cursor.fetchone()
        if row:
            return {
                "user_id": row[0],
                "native_lang": row[1],
                "target_lang": row[2],
                "style": row[3],
                "gender": row[4],
                "promo_code_used": row[5],        # 🟡 загружаем код
                "promo_type": row[6],             # 🟡 загружаем тип
                "promo_activated_at": row[7],     # 🟡 загружаем дату
                "promo_days": row[8]              # 🟡 загружаем срок
            }
        else:
            return {
                "user_id": user_id,
                "native_lang": None,
                "target_lang": None,
                "style": None,
                "gender": None,
                "promo_code_used": None,         # 🟡 по умолчанию нет промо
                "promo_type": None,
                "promo_activated_at": None,
                "promo_days": None
            }


# 🟡 добавлено: сохранить пол пользователя, если он ещё не сохранён

def save_user_gender(user_id, gender):
    profile = load_user_profile(user_id)
    if not profile.get("gender"):
        profile["gender"] = gender
        save_user_profile(user_id, profile)
