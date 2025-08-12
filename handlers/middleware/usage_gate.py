from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes, ApplicationHandlerStop
from telegram.constants import MessageEntityType
from components.access import has_access
from components.usage_db import get_usage, increment_usage
from components.offer_texts import OFFER
from components.promo import is_promo_valid  # добавили проверку промокодов

FREE_DAILY_LIMIT = 15
REMIND_AFTER = 10

def _ui_lang(ctx: ContextTypes.DEFAULT_TYPE) -> str:
    return ctx.user_data.get("ui_lang", "ru")

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

    # Если есть премиум-доступ или активный промокод — пропускаем
    if has_access(user_id) or is_promo_valid(user_id):
        return

    used = get_usage(user_id)
    lang = _ui_lang(ctx)

    if used >= FREE_DAILY_LIMIT:
        await (update.message or update.edited_message).reply_text(OFFER["limit_reached"][lang])
        raise ApplicationHandlerStop

    used = increment_usage(user_id)

    if used == REMIND_AFTER:
        await (update.message or update.edited_message).reply_text(OFFER["reminder_after_10"][lang])

    if used > FREE_DAILY_LIMIT:
        await (update.message or update.edited_message).reply_text(OFFER["limit_reached"][lang])
        raise ApplicationHandlerStop
