# components/i18n.py
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from components.profile_db import get_user_profile

# На случай отсутствия state.session.user_sessions — безопасный фолбэк
try:
    from state.session import user_sessions  # type: ignore
except Exception:  # pragma: no cover
    user_sessions = {}  # type: ignore


def _pick_profile(update: Update) -> dict:
    """
    Возвращает наиболее «языково-информативный» профиль.
    Сначала пробуем user_id, затем chat_id. Предпочитаем тот,
    где есть interface_lang/target_lang.
    """
    prof_user = {}
    prof_chat = {}
    try:
        prof_user = get_user_profile(update.effective_user.id) or {}
    except Exception:
        prof_user = {}
    try:
        prof_chat = get_user_profile(update.effective_chat.id) or {}
    except Exception:
        prof_chat = {}

    # Отдаём тот, где явно указан язык
    for p in (prof_user, prof_chat):
        if p.get("interface_lang") or p.get("target_lang"):
            return p
    # Иначе — любой непустой
    return prof_user or prof_chat or {}


def get_ui_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Единый резолвер языка интерфейса.
    Приоритет:
    1) ctx.user_data["ui_lang"] (если уже выбран/прогрет)
    2) state.session.user_sessions[chat_id]["interface_lang"] (во время онбординга)
    3) Профиль из БД (user_id → chat_id), поля interface_lang/target_lang
    4) "en" по умолчанию
    """
    # 1) Быстрый путь из user_data
    lang = (getattr(ctx, "user_data", None) or {}).get("ui_lang")
    if lang:
        return lang

    # 2) Во время онбординга язык может лежать в сессии
    try:
        sess = (user_sessions or {}).get(update.effective_chat.id, {}) or {}
        if isinstance(sess, dict) and sess.get("interface_lang"):
            return sess["interface_lang"]
    except Exception:
        pass

    # 3) Профиль из БД (user_id → chat_id)
    profile = _pick_profile(update)
    if profile.get("interface_lang"):
        return profile["interface_lang"]
    if profile.get("target_lang"):
        return profile["target_lang"]

    # 4) Фолбэк
    return "en"
