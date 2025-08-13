from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes, ApplicationHandlerStop
from telegram.constants import MessageEntityType
from components.access import has_access
from components.usage_db import get_usage, increment_usage
from components.offer_texts import OFFER
from components.promo import is_promo_valid          # ✅ проверка активного промо по профилю
from components.profile_db import get_user_profile   # ✅ берём профиль пользователя

FREE_DAILY_LIMIT = 15
REMIND_AFTER = 10

from components.profile_db import get_user_profile

def _ui_lang(ctx: ContextTypes.DEFAULT_TYPE, user_id: int | None = None) -> str:
    ui = ctx.user_data.get("ui_lang") if getattr(ctx, 'user_data', None) else None
    if ui:
        return ui
    if user_id is None:
        return 'ru'
    prof = get_user_profile(user_id) or {}
    ui = prof.get('interface_lang', 'ru')
    try:
        ctx.user_data['ui_lang'] = ui
    except Exception:
        pass
    return ui

def _is_countable_message(update: Update) -> bool:
    msg = update.message or update.edited_message
    if not msg:
        return False
    if msg.from_user and msg.from_user.is_bot:
        return False
    if msg.text and msg.text.startswith("/"):
        return False
    if msg.entities:
        for e in msg.entities:
            if e.type in (MessageEntityType.BOT_COMMAND,):
                return False
    return bool(msg.text or msg.voice or msg.audio)

async def usage_gate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_countable_message(update):
        return

    user_id = update.effective_user.id

    # 1) Премиум — всегда пропускаем
    if has_access(user_id):
        return

    # 2) Активный промокод — тоже пропускаем
    profile = get_user_profile(user_id) or {}
    if is_promo_valid(profile):
        return

    # 3) Счётчик бесплатных сообщений
    used = get_usage(user_id)
    lang = _ui_lang(ctx, user_id)

    if used >= FREE_DAILY_LIMIT:
        await (update.message or update.edited_message).reply_text(
            OFFER["limit_reached"][lang]
            + ("\n\n💡 " + ("Введите /promo для активации промокода и продолжения."
                            if lang == "ru" else
                            "Enter /promo to activate a promo code and continue."))
        )
        raise ApplicationHandlerStop

    used = increment_usage(user_id)

    if used == REMIND_AFTER:
        await (update.message or update.edited_message).reply_text(OFFER["reminder_after_10"][lang])

    if used > FREE_DAILY_LIMIT:
        await (update.message or update.edited_message).reply_text(
            OFFER["limit_reached"][lang]
            + ("\n\n💡 " + ("Введите /promo для активации промокода и продолжения."
                            if lang == "ru" else
                            "Enter /promo to activate a promo code and continue."))
        )
        raise ApplicationHandlerStop
