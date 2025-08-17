from __future__ import annotations
import logging
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

logger = logging.getLogger("usage_gate")

# >>> Диагностика: подтверждаем загрузку модуля при старте приложения
logger.info("[gate] module loaded")

FREE_DAILY_LIMIT = 15
REMIND_AFTER = 10

def _offer_text(key: str, lang: str) -> str:
    d = OFFER.get(key) if isinstance(OFFER, dict) else None
    if not isinstance(d, dict):
        return ""
    if lang in d:
        return d[lang]
    # Фолбэк: сначала en, потом ru, потом любая доступная
    return d.get("en") or d.get("ru") or next(iter(d.values()), "")

def _ui_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    try:
        lang = get_ui_lang(update, ctx)  # учитывает user_data / онбординг / профиль
        return lang
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
    # Диагностика входа в гейт
    try:
        uid = getattr(update.effective_user, "id", None)
        cid = getattr(update.effective_chat, "id", None)
        snippet = (getattr(update.message, "text", "") or "")[:60]
        logger.info("[gate] enter user=%s chat=%s text=%r", uid, cid, snippet)
    except Exception:
        pass

    # Пока активна пауза (режим /teach)
    if ctx.chat_data.get("dialog_paused"):
        logger.info("[gate] dialog_paused=True -> pass through")
        return

    if not _is_countable_message(update):
        logger.info("[gate] not countable -> pass through")
        return

    # Во время ввода промокода на онбординге
    try:
        chat_id = update.effective_chat.id
        sess = user_sessions.get(chat_id, {}) or {}
        if sess.get("onboarding_stage") == "awaiting_promo":
            logger.info("[gate] onboarding awaiting_promo -> pass through")
            return
    except Exception:
        pass

    user_id = update.effective_user.id

    # Премиум — пропускаем
    if has_access(user_id):
        logger.info("[gate] has_access=True -> pass through")
        return

    # Активный промокод — пропускаем
    profile = get_user_profile(user_id) or {}
    if is_promo_valid(profile):
        logger.info("[gate] promo valid -> pass through")
        return

    # Счётчик бесплатных сообщений
    used = get_usage(user_id)
    lang = _ui_lang(update, ctx)

    limit_text = _offer_text("limit_reached", lang) or (
        "Лимит пробного дня достигнут." if lang == "ru" else "You’ve hit the daily trial limit."
    )
    reminder_text = _offer_text("reminder_after_10", lang) or (
        "Осталось 5 сообщений в пробном периоде." if lang == "ru" else "You’ve got 5 messages left on the trial."
    )

    logger.info("[gate] usage before increment = %s (limit=%s)", used, FREE_DAILY_LIMIT)

    if used >= FREE_DAILY_LIMIT:
        hint = ("\n\n💡 Введите /promo для активации промокода и продолжения."
                if lang == "ru"
                else "\n\n💡 Enter /promo to activate a promo code and continue.")
        await (update.message or update.edited_message).reply_text(limit_text + hint)
        logger.info("[gate] limit reached -> stop")
        raise ApplicationHandlerStop

    used = increment_usage(user_id)
    logger.info("[gate] usage after increment = %s", used)

    if used == REMIND_AFTER:
        hint = ("\n\n💡 Есть промокод? Введите /promo <код>."
                if lang == "ru"
                else "\n\n💡 Have a promo code? Use /promo <code>.")
        await (update.message or update.edited_message).reply_text(reminder_text + hint)

    if used > FREE_DAILY_LIMIT:
        hint = ("\n\n💡 Введите /promo для активации промокода и продолжения."
                if lang == "ru"
                else "\n\n💡 Enter /promo to activate a promo code and continue.")
        await (update.message or update.edited_message).reply_text(limit_text + hint)
        logger.info("[gate] limit exceeded after increment -> stop")
        raise ApplicationHandlerStop
