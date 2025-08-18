from __future__ import annotations
import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes, ApplicationHandlerStop
from telegram.constants import MessageEntityType

from components.access import has_access
from components.usage_db import get_usage, increment_usage
from components.offer_texts import OFFER
from components.promo import is_promo_valid
from components.profile_db import get_user_profile
from components.i18n import get_ui_lang
from state.session import user_sessions

logger = logging.getLogger("english-bot")
logger.info("[gate] module loaded")

FREE_DAILY_LIMIT = 15
REMIND_AFTER = 10

def _offer_text(key: str, lang: str) -> str:
    d = OFFER.get(key) if isinstance(OFFER, dict) else None
    if not isinstance(d, dict):
        return ""
    if lang in d:
        return d[lang]
    return d.get("en") or d.get("ru") or next(iter(d.values()), "")

def _ui_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    try:
        return get_ui_lang(update, ctx)
    except Exception:
        return (ctx.user_data or {}).get("ui_lang", "en")

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
    # Диагностика входа
    try:
        uid = getattr(update.effective_user, "id", None)
        cid = getattr(update.effective_chat, "id", None)
        snippet = (getattr(update.message, "text", "") or "")[:60]
        logger.info("[gate] enter user=%s chat=%s text=%r", uid, cid, snippet)
    except Exception:
        pass

    # Считаем только «диалоговые» сообщения (не команды, не от бота и т.п.)
    if not _is_countable_message(update):
        logger.info("[gate] not countable -> pass through")
        return

    # Достаём chat_id/session один раз
    chat_id = getattr(update.effective_chat, "id", None)
    sess = user_sessions.get(chat_id, {}) or {}

    # Во время ввода промокода на онбординге — ничего не считаем/не блокируем
    if sess.get("onboarding_stage") == "awaiting_promo":
        logger.info("[gate] awaiting_promo -> pass through")
        return

    user_id = getattr(update.effective_user, "id", None)

    # Премиум — пропускаем
    try:
        premium = await asyncio.to_thread(has_access, user_id)
    except Exception:
        logger.exception("[gate] has_access failed; treating as no access")
        premium = False
    if premium:
        logger.info("[gate] has_access=True -> pass through")
        return

    # Профиль берём по chat_id (в твоей БД ключ — chat_id)
    try:
        profile = await asyncio.to_thread(get_user_profile, chat_id)
        profile = profile or {}
    except Exception:
        logger.exception("[gate] get_user_profile failed; assuming empty profile")
        profile = {}

    # «Дольём» недостающие промо-поля из session (важно для минутных кодов и т.п.)
    for k in ("promo_code_used", "promo_type", "promo_activated_at", "promo_days", "promo_minutes", "promo_used_codes"):
        if k not in profile and k in sess:
            profile[k] = sess[k]

    # Активный промо — пропускаем
    if is_promo_valid(profile):
        logger.info("[gate] promo valid -> pass through")
        return

    # Счётчик бесплатных сообщений считаем по user_id (как и раньше)
    try:
        used = await asyncio.to_thread(get_usage, user_id)
    except Exception:
        logger.exception("[gate] get_usage failed; fallback used=0")
        used = 0

    ui = _ui_lang(update, ctx)

    limit_text = _offer_text("limit_reached", ui) or (
        "Лимит пробного дня достигнут." if ui == "ru" else "You’ve hit the daily trial limit."
    )
    reminder_text = _offer_text("reminder_after_10", ui) or (
        "Осталось 5 сообщений в пробном периоде." if ui == "ru" else "You’ve got 5 messages left on the trial."
    )

    logger.info("[gate] usage before increment = %s (limit=%s)", used, FREE_DAILY_LIMIT)

    # Уже достигли лимита — блокируем до промо/покупки
    if used >= FREE_DAILY_LIMIT:
        hint = ("\n\n💡 Введите /promo для активации промокода и продолжения."
                if ui == "ru"
                else "\n\n💡 Enter /promo to activate a promo code and continue.")
        await (update.message or update.edited_message).reply_text(limit_text + hint)
        logger.info("[gate] limit reached -> stop")
        raise ApplicationHandlerStop

    # Инкремент
    try:
        used = await asyncio.to_thread(increment_usage, user_id)
    except Exception:
        logger.exception("[gate] increment_usage failed; treating as exceeded")
        used = FREE_DAILY_LIMIT + 1

    logger.info("[gate] usage after increment = %s", used)

    # Напоминание на 10-м
    if used == REMIND_AFTER:
        hint = ("\n\n💡 Есть промокод? Введите /promo <код>."
                if ui == "ru"
                else "\n\n💡 Have a promo code? Use /promo <code>.")
        await (update.message or update.edited_message).reply_text(reminder_text + hint)

    # Перешагнули лимит после инкремента — блокируем
    if used > FREE_DAILY_LIMIT:
        hint = ("\n\n💡 Введите /promo для активации промокода и продолжения."
                if ui == "ru"
                else "\n\n💡 Enter /promo to activate a promo code and continue.")
        await (update.message or update.edited_message).reply_text(limit_text + hint)
        logger.info("[gate] limit exceeded after increment -> stop")
        raise ApplicationHandlerStop
