from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'user_profiles.db'))


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("PRAGMA busy_timeout=5000;")
    return conn, cur


def init_promo_db() -> None:
    conn, cur = _connect()
    try:
        # promo_codes: single-use (global) + per-user one-time for shareable codes
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                days INTEGER,
                lang_policy TEXT NOT NULL,
                lang_slots INTEGER NOT NULL,
                is_single_use INTEGER NOT NULL DEFAULT 0,   -- global single-use
                per_user_once INTEGER NOT NULL DEFAULT 0,   -- each user can redeem once
                active INTEGER NOT NULL DEFAULT 1,
                notes TEXT,
                redeemed_by INTEGER,
                redeemed_at TEXT
            )
            """
        )

        # Auto-migrate older schema (if table existed without per_user_once)
        cur.execute("PRAGMA table_info(promo_codes)")
        cols = {row[1] for row in cur.fetchall()}
        if "per_user_once" not in cols:
            cur.execute("ALTER TABLE promo_codes ADD COLUMN per_user_once INTEGER NOT NULL DEFAULT 0")

        # Redemption log (for per-user-one-time codes)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS promo_redemptions (
                code TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                redeemed_at TEXT NOT NULL,
                PRIMARY KEY (code, user_id)
            )
            """
        )

        conn.commit()
    finally:
        conn.close()


def seed_default_codes() -> None:
    """Insert default promo codes if they don't exist.

    Agreed defaults:
      - WESTERN: english_only, unlimited, permanent, multi-use
      - 1709: all, unlimited, permanent, multi-use
      - FRIEND/друг: shareable multi-use, BUT each user can redeem only once; unlimited, 3 days; 1 language switchable
    """
    init_promo_db()
    defaults = [
        # code, kind, days, policy, slots, is_single_use, per_user_once, notes
        ("western", "WESTERN", None, "english_only", 1, 0, 0, "partner code: English-only unlimited"),
        ("1709", "ALL_PERMANENT", None, "all", 999, 0, 0, "private multi-use all languages unlimited"),
        ("friend", "FRIEND_3D", 3, "all", 1, 0, 1, "shareable: each user once, 1 language (switchable), unlimited, 3 days"),
        ("друг", "FRIEND_3D", 3, "all", 1, 0, 1, "shareable alias (RU): each user once"),
    ]

    conn, cur = _connect()
    try:
        for code, kind, days, pol, slots, single_use, per_user_once, notes in defaults:
            cur.execute(
                """
                INSERT OR IGNORE INTO promo_codes
                (code, kind, days, lang_policy, lang_slots, is_single_use, per_user_once, active, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (code, kind, days, pol, int(slots), int(single_use), int(per_user_once), notes),
            )
        conn.commit()
    finally:
        conn.close()


def get_code(code: str) -> Optional[Dict[str, Any]]:
    if not code:
        return None
    seed_default_codes()  # safe no-op after first run
    conn, cur = _connect()
    try:
        cur.execute(
            """SELECT code, kind, days, lang_policy, lang_slots, is_single_use, per_user_once, active, notes, redeemed_by, redeemed_at
                 FROM promo_codes WHERE code=?""",
            (code,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "code": row[0],
            "kind": row[1],
            "days": row[2],
            "lang_policy": row[3],
            "lang_slots": row[4],
            "is_single_use": int(row[5] or 0),
            "per_user_once": int(row[6] or 0),
            "active": int(row[7] or 0),
            "notes": row[8],
            "redeemed_by": row[9],
            "redeemed_at": row[10],
        }
    finally:
        conn.close()


def _redeem_per_user(code: str, user_id: int) -> Tuple[bool, str]:
    """Return ok if (code,user_id) not redeemed yet; then record redemption."""
    conn, cur = _connect()
    try:
        now = datetime.now(timezone.utc).isoformat()
        try:
            cur.execute(
                "INSERT INTO promo_redemptions (code, user_id, redeemed_at) VALUES (?, ?, ?)",
                (code, int(user_id), now),
            )
            conn.commit()
            return True, "ok"
        except sqlite3.IntegrityError:
            # already redeemed by this user
            return False, "already_used_by_you"
    finally:
        conn.close()


def redeem(code: str, user_id: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Redeem promo code.
    - Global single-use: only one user total.
    - Per-user-once: many users can redeem, but each user only once.
    - Otherwise: multi-use without limits.
    """
    rec = get_code(code)
    if not rec or not int(rec.get("active") or 0):
        return False, "invalid", None

    # 1) per-user once (your 'friend/друг')
    if int(rec.get("per_user_once") or 0):
        ok, reason = _redeem_per_user(code, user_id)
        return (ok, reason, rec)

    # 2) global single-use
    if int(rec.get("is_single_use") or 0):
        if rec.get("redeemed_by"):
            return False, "already_used", rec

        now = datetime.now(timezone.utc).isoformat()
        conn, cur = _connect()
        try:
            # atomic: redeem only if still unused
            cur.execute(
                """
                UPDATE promo_codes
                SET redeemed_by=?, redeemed_at=?
                WHERE code=? AND (redeemed_by IS NULL OR redeemed_by=0)
                """,
                (int(user_id), now, code),
            )
            conn.commit()
        finally:
            conn.close()

        rec2 = get_code(code)
        if rec2 and rec2.get("redeemed_by") == int(user_id):
            return True, "ok", rec2
        return False, "already_used", rec2

    # 3) fully multi-use
    return True, "ok", rec
