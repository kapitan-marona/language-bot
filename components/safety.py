# components/safety.py
from __future__ import annotations
from typing import Tuple, Any
from telegram import Update
from telegram.ext import ContextTypes

# Импортируем исходные функции — сигнатуры могут различаться в старых/новых версиях
from components.promo import check_promo_code as _orig_check  # type: ignore
from components.promo import activate_promo as _orig_activate  # type: ignore


def call_check_promo_code(code: str, profile: dict | None = None) -> tuple[bool, str | None, dict | None]:
    """
    Унифицированный вызов check_promo_code для разных реализаций:

    Вариант A (как у тебя сейчас):
        check_promo_code(code) -> dict | None  (info или None)
    Вариант B (старые билды):
        check_promo_code(code, profile) -> (ok: bool, msg: str | None, info: dict | None)

    Возвращаем (ok, msg, info) в едином формате.
    """
    # 1) Пробуем новую сигнатуру (1 аргумент)
    try:
        res = _orig_check(code)  # type: ignore
    except TypeError:
        # 2) Падаем на старую сигнатуру (2 аргумента)
        res = _orig_check(code, profile)  # type: ignore

    # Нормализуем результат к (ok, msg, info)
    if isinstance(res, tuple):
        # ожидаем (ok, msg, info) или совместимую форму
        ok = bool(res[0]) if len(res) > 0 else False
        msg = res[1] if len(res) > 1 else None
        info = res[2] if len(res) > 2 else None
        return ok, msg, info

    if isinstance(res, dict):
        # новая сигнатура: вернулся info
        return True, None, res

    if res is None or res is False:
        return False, None, None

    # На всякий случай: любое truthy значение — считаем успехом без info
    return bool(res), None, res if isinstance(res, dict) else None


def call_activate_promo(profile_or_id: Any, code_or_info: Any) -> tuple[bool, str | None]:
    """
    Унифицированный вызов activate_promo для разных реализаций:

    Вариант A (как у тебя сейчас):
        activate_promo(profile: dict, code: str) -> (ok: bool, reason: str)
            — профиль модифицируется на месте (promo_* поля).
    Вариант B (старые билды):
        activate_promo(chat_id: int, info: dict) -> bool | (ok: bool, reason: str)

    Возвращаем (ok, reason) в едином формате.
    """
    # 1) Пробуем «новую» сигнатуру (dict, str)
    try:
        ok, reason = _orig_activate(profile_or_id, code_or_info)  # type: ignore
        # если вдруг реализация вернула не кортеж, а bool
        if not isinstance(ok, (bool, int)):  # странный ответ — нормализуем ниже
            raise TypeError
        return bool(ok), reason if isinstance(reason, str) else None
    except TypeError:
        # 2) Пробуем «старую» сигнатуру (chat_id, info)
        res = _orig_activate(profile_or_id, code_or_info)  # type: ignore
        if isinstance(res, tuple):
            ok = bool(res[0]) if len(res) > 0 else False
            reason = res[1] if len(res) > 1 else None
            return ok, reason
        return bool(res), None


async def safe_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE, text: str, **kwargs):
    """
    Безопасный ответ пользователю:
    1) пробуем reply на effective_message,
    2) иначе отправляем новое сообщение в чат.
    """
    msg = getattr(update, "effective_message", None)
    if msg:
        try:
            return await msg.reply_text(text, **kwargs)
        except Exception:
            pass
    try:
        chat_id = update.effective_chat.id
        return await ctx.bot.send_message(chat_id, text, **kwargs)
    except Exception:
        return None


def offer_text(OFFER: dict, key: str, ui: str, default_ru: str = "", default_en: str = "") -> str:
    """
    Безопасно достаём строку из OFFER[key] по языку ui с фолбэками.
    """
    d = OFFER.get(key) if isinstance(OFFER, dict) else None
    if isinstance(d, dict):
        return d.get(ui) or d.get("en") or d.get("ru") or next(iter(d.values()), "")
    return default_ru if ui == "ru" else default_en
