# components/profile_db.py
from __future__ import annotations
import os
import sqlite3
from typing import Any, Dict, Optional

# Абсолютный путь к файлу БД рядом с проектом
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'user_profiles.db'))

# NEW: safe profile reset helper
def clear_user_profile(chat_id: int) -> None:
    """Сбрасывает поля профиля (оставляя строку либо создавая пустую)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM user_profiles WHERE chat_id = ?", (chat_id,))
    exists = cur.fetchone() is not None
    if exists:
        cur.execute(
            """
            UPDATE user_profiles
            SET name=NULL, interface_lang=NULL, target_lang=NULL, level=NULL, style=NULL,
                promo_code_used=NULL, promo_type=NULL, promo_activated_at=NULL, promo_days=NULL
            WHERE chat_id=?
            """,
            (chat_id,),
        )
    else:
        cur.execute(
            """
            INSERT INTO user_profiles (chat_id)
            VALUES (?)
            """,
            (chat_id,),
        )
    conn.commit()
    conn.close()


def init_db() -> None:
    """Инициализация БД и безопасная авто-миграция недостающих колонок.

    Таблица user_profiles может уже существовать у старых пользователей —
    ...
    """
    # (остальной код инициализации без изменений)
    ...

def get_user_profile(chat_id: int) -> Optional[Dict[str, Any]]:
    ...
    # (без изменений)

def save_user_profile(
    chat_id: int,
    *,
    name: Optional[str] = None,
    interface_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
    level: Optional[str] = None,
    style: Optional[str] = None,
    # Поля промо можно тоже сохранять через этот метод при желании
    promo_code_used: Optional[str] = None,
    promo_type: Optional[str] = None,
    promo_activated_at: Optional[str] = None,
    promo_days: Optional[int] = None,
) -> None:
    """Обновляет/создаёт профиль пользователя частично (upsert)."""
    current = get_user_profile(chat_id) or {"chat_id": chat_id}
    ...
    # (без изменений)

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
            UPDATE user_profiles
            SET promo_code_used = ?, promo_type = ?, promo_activated_at = ?, promo_days = ?
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
