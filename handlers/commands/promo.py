from __future__ import annotations
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from components.promo import check_promo_code, activate_promo, format_promo_status_for_user
from components.profile_db import get_user_profile, save_user_profile
from components.i18n import get_ui_lang


async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /promo            -> показать статус
    /promo <код>      -> активировать код и показать статус
    """
    chat_id = update.effective_chat.id
    args = context.args or []
    ui = get_ui_lang(update, context)

    # читаем профиль из БД (в пуле потоков)
    profile = await asyncio.to_thread(get_user_profile, chat_id)
    if not profile:
        profile = {"chat_id": chat_id}

    # если указан код — пытаемся активировать
    if args:
        code = (args[0] or "").strip()
        info = check_promo_code(code)
        if not info:
            await update.message.reply_text("❌ неизвестный промокод" if ui == "ru" else "❌ unknown promo code")
            return

        ok, reason = activate_promo(profile, code)
        if not ok:
            # already_used / invalid / etc.
            await update.message.reply_text(
                "Этот код уже использовался." if ui == "ru" and reason == "already_used"
                else ("⚠️ не удалось активировать промокод" if ui == "ru" else "⚠️ failed to activate promo code")
            )
            return

        # Сохраняем промо-поля в БД (включая minutes и историю использованных кодов)
        await asyncio.to_thread(
            save_user_profile,
            chat_id,
            promo_code_used=profile.get("promo_code_used"),
            promo_type=profile.get("promo_type"),
            promo_activated_at=profile.get("promo_activated_at"),
            promo_days=profile.get("promo_days"),
            promo_minutes=profile.get("promo_minutes"),
            promo_used_codes=profile.get("promo_used_codes"),
        )

        await update.message.reply_text(format_promo_status_for_user(profile, ui))
        return

    # без кода — просто статус
    await update.message.reply_text(format_promo_status_for_user(profile, ui))
