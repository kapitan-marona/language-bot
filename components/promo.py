# handlers/commands/promo.py
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes

from components.profile_db import get_user_profile
from components.promo import normalize_code, format_promo_status_for_user
from components.i18n import get_ui_lang
from components.safety import (
    call_check_promo_code,
    call_activate_promo,
    safe_reply,
    safe_save_user_profile,
)
from state.session import user_sessions


async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /promo              → показать статус
    /promo <код>        → активировать код и показать статус (+ сообщение, что лимит снят)

    Совместимо с обеими реализациями components.promo.{check_promo_code, activate_promo}
    и с текущей схемой БД (через safe_save_user_profile).
    """
    chat_id = update.effective_chat.id
    ui = get_ui_lang(update, context)
    args = context.args or []

    # Профиль из БД + подмешаем данные из сессии (например, promo_used_codes)
    profile = get_user_profile(chat_id) or {"chat_id": chat_id}
    sess = user_sessions.setdefault(chat_id, {})
    if sess.get("promo_used_codes") and not profile.get("promo_used_codes"):
        # База не хранит, но чтобы не давать повторно вводить тот же код в текущем процессе — используем из сессии
        profile["promo_used_codes"] = list(sess["promo_used_codes"])

    # Без аргументов — показать статус (локализованно)
    if not args:
        await safe_reply(update, context, format_promo_status_for_user(profile, ui))
        return

    # Нормализуем и проверяем код
    code = normalize_code(" ".join(args))

    ok_check, msg_check, _info = call_check_promo_code(code, profile)
    if not ok_check:
        # Сообщение из старой реализации может быть не локализовано — дадим фолбэк
        fallback = "❌ неизвестный промокод" if ui == "ru" else "❌ unknown promo code"
        await safe_reply(update, context, msg_check or fallback)
        return

    # Активируем (унифицированный адаптер); profile модифицируется на месте
    ok_act, reason = call_activate_promo(profile, code)

    if ok_act:
        # Сохраним профиль через безопасный адаптер (лишние поля будут отброшены без ошибок)
        safe_save_user_profile(
            chat_id,
            promo_code_used=profile.get("promo_code_used"),
            promo_type=profile.get("promo_type"),
            promo_activated_at=profile.get("promo_activated_at"),
            promo_days=profile.get("promo_days"),
            promo_minutes=profile.get("promo_minutes"),     # если схема не знает — адаптер отбросит
            promo_used_codes=profile.get("promo_used_codes")  # dto: оставим для совместимости на будущее
        )

        # Актуализируем сессию, чтобы «уже использован» работал в текущем процессе
        if profile.get("promo_used_codes") is not None:
            sess["promo_used_codes"] = list(profile["promo_used_codes"])

        # Покажем статус и мягко сообщим о снятии лимита
        await safe_reply(update, context, format_promo_status_for_user(profile, ui))
        tail = ("✅ Лимит сообщений снят — можно продолжать!"
                if ui == "ru"
                else "✅ Message limit removed — you can continue!")
        await safe_reply(update, context, tail)
        return

    # Не удалось активировать — локализуем причину
    reason_map = {
        "already_used": ("⚠️ Промокод уже был активирован ранее." if ui == "ru"
                         else "⚠️ Promo code was already used."),
        "invalid": ("⚠️ Такой промокод не найден." if ui == "ru"
                    else "⚠️ Promo code not found."),
        # можно расширять по мере необходимости
    }
    fallback = "⚠️ не удалось активировать промокод" if ui == "ru" else "⚠️ failed to activate promo code"
    await safe_reply(update, context, reason_map.get(reason or "", fallback))
