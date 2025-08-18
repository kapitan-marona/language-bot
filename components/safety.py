# components/safety.py
from __future__ import annotations
from typing import Tuple, Any
from telegram import Update
from telegram.ext import ContextTypes
import inspect

# Импортируем оригинальные функции (их сигнатуры могут отличаться между версиями)
from components.promo import check_promo_code as _orig_check  # type: ignore
from components.promo import activate_promo as _orig_activate  # type: ignore

# ---------- Адаптеры промо ----------

def call_check_promo_code(code: str, profile: dict | None = None) -> tuple[bool, str | None, dict | None]:
    """
    Унифицированный вызов check_promo_code для разных реализаций:

    Вариант A (новая логика):
        check_promo_code(code) -> dict | None  (info или None)
    Вариант B (старые билды):
        check_promo_code(code, profile) -> (ok: bool, msg: str | None, info: dict | None)

    Всегда возвращаем (ok, msg, info).
    """
    try:
        res = _orig_check(code)  # type: ignore
    except TypeError:
        # старая сигнатура
        res = _orig_check(code, profile)  # type: ignore

    if isinstance(res, tuple):
        ok = bool(res[0]) if len(res) > 0 else False
        msg = res[1] if len(res) > 1 else None
        info = res[2] if len(res) > 2 else None
        return ok, msg, info

    if isinstance(res, dict):
        return True, None, res

    if res is None or res is False:
        return False, None, None

    return bool(res), None, res if isinstance(res, dict) else None


def call_activate_promo(profile_or_id: Any, code_or_info: Any) -> tuple[bool, str | None]:
    """
    Унифицированный вызов activate_promo для разных реализаций:

    Вариант A (новая логика):
        activate_promo(profile: dict, code: str) -> (ok: bool, reason: str)

    Вариант B (старые билды):
        activate_promo(chat_id: int, info: dict) -> bool | (ok: bool, reason: str)
    """
    try:
        ok, reason = _orig_activate(profile_or_id, code_or_info)  # type: ignore
        if not isinstance(ok, (bool, int)):
            raise TypeError
        return bool(ok), reason if isinstance(reason, str) else None
    except TypeError:
        res = _orig_activate(profile_or_id, code_or_info)  # type: ignore
        if isinstance(res, tuple):
            ok = bool(res[0]) if len(res) > 0 else False
            reason = res[1] if len(res) > 1 else None
            return ok, reason
        return bool(res), None

# ---------- Безопасные обёртки общения ----------

async def safe_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE, text: str, **kwargs):
    """
    Безопасный ответ:
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

# ---------- ВАЖНО: безопасное сохранение профиля (фильтруем лишние kwargs) ----------

def safe_save_user_profile(chat_id: int, **kwargs) -> None:
    """
    Вызывает components.profile_db.save_user_profile, отбрасывая неизвестные аргументы.
    Нужен для совместимости, когда код передаёт новые поля (напр. promo_minutes, promo_used_codes),
    а старая схема БД/сигнатура save_user_profile их не принимает.
    """
    try:
        from components.profile_db import save_user_profile as _save  # импорт тут, чтобы избежать циклов
    except Exception:
        return

    # 1) Пытаемся вызвать «как есть»
    try:
        _save(chat_id, **kwargs)
        return
    except TypeError:
        pass  # будем фильтровать

    # 2) Узнаём, какие имена параметров реально принимает функция
    try:
        sig = inspect.signature(_save)
        allowed = {
            p.name
            for p in sig.parameters.values()
            if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        }
        # chat_id — позиционный, в kwargs его нет
        filtered = {k: v for k, v in kwargs.items() if k in allowed}
        try:
            _save(chat_id, **filtered)
            return
        except Exception:
            pass
    except Exception:
        pass

    # 3) Жёсткий фолбэк: оставим только базовые, которые есть у твоей текущей схемы
    basic = {
        "name", "interface_lang", "target_lang", "level", "style",
        "promo_code_used", "promo_type", "promo_activated_at", "promo_days",
    }
    filtered = {k: v for k, v in kwargs.items() if k in basic}
    try:
        _save(chat_id, **filtered)
    except Exception:
        # если не получилось — молча игнорируем, чтобы не ронять обработчик
        return
