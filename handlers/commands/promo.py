# handlers/commands/promo.py
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes

from components.profile_db import get_user_profile, save_user_profile
from components.promo import normalize_code, format_promo_status_for_user  # используем твою функцию статуса
from components.i18n import get_ui_lang
from components.safety import call_check_promo_code, call_activate_promo, safe_reply

# NEW: импорт хелпера стикеров
from handlers.chat.chat_handler import maybe_send_sticker


async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /promo              → показать статус
    /promo <код>        → активировать код и показать статус (+ сообщение, что лимит снят)
    Совместимо с обеими реализациями components.promo.{check_promo_code, activate_promo}.
    """
    chat_id = update.effective_chat.id
    ui = get_ui_lang(update, context)
    args = context.args or []

    profile = get_user_profile(chat_id) or {"chat_id": chat_id}

    # Без аргументов — показать текущий статус (на нужном языке)
    if not args:
        await safe_reply(update, context, format_promo_status_for_user(profile, ui))
        return

    # Нормализуем и проверяем код
    code = normalize_code(" ".join(args))

    ok_check, msg_check, info = call_check_promo_code(code, profile)

    if not ok_check:
        # Сообщение в msg_check может быть только на RU в старых билдах — даём локализованный фолбэк
        fallback = "❌ неизвестный промокод" if ui == "ru" else "❌ unknown promo code"
        await safe_reply(update, context, msg_check or fallback)
        return

    # Активируем (унифицированный адаптер) — твой текущий путь: (profile, code)
    ok_act, reason = call_activate_promo(profile, code)

    if ok_act:
        # Сохраняем профиль (значения уже положены в profile активатором)
        save_user_profile(
            chat_id,
            promo_code_used=profile.get("promo_code_used"),
            promo_type=profile.get("promo_type"),
            promo_activated_at=profile.get("promo_activated_at"),
            promo_days=profile.get("promo_days"),
        )
        await safe_reply(update, context, format_promo_status_for_user(profile, ui))
        tail = ("✅ Лимит сообщений снят — можно продолжать!"
                if ui == "ru"
                else "✅ Message limit removed — you can continue!")
        await safe_reply(update, context, tail)
        # NEW: «иногда» — 0.7 по ТЗ
        await maybe_send_sticker(context, update.effective_chat.id, "fire", chance=0.7)
        return

    # Не удалось активировать — локализуем причину
    reason_map = {
        "already_used": ("⚠️ Промокод уже был активирован ранее." if ui == "ru"
                         else "⚠️ Promo code was already used."),
        "invalid": ("⚠️ Такой промокод не найден." if ui == "ru"
                    else "⚠️ Promo code not found."),
    }
    fallback = "⚠️ не удалось активировать промокод" if ui == "ru" else "⚠️ failed to activate promo code"
    await safe_reply(update, context, reason_map.get(reason or "", fallback))
