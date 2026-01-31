from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, ApplicationHandlerStop
from telegram.constants import MessageEntityType

from components.access import get_profile, has_unlimited_messages
from components.usage_db import get_usage, increment_usage
from components.offer_texts import OFFER
from components.profile_db import get_user_profile, save_user_profile
from components.i18n import get_ui_lang
from state.session import user_sessions

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
        # в проекте уже есть get_ui_lang(update, ctx)
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
    # считаем текст/голос/аудио
    return bool(msg.text or msg.voice or msg.audio)


def _get_session(update: Update) -> dict:
    """Единая сессия: user_id как основной ключ + алиас chat_id (обратная совместимость)."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    sess = user_sessions.get(user_id)
    if not sess:
        legacy = user_sessions.get(chat_id)
        if legacy:
            sess = legacy
            user_sessions[user_id] = sess
        else:
            sess = {}
            user_sessions[user_id] = sess

    if chat_id != user_id:
        user_sessions[chat_id] = sess

    return sess


async def _ensure_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    u = update.effective_user
    if not u:
        return
    try:
        if not get_user_profile(u.id):
            save_user_profile(
                u.id,
                name=(u.full_name or u.username or ""),
                interface_lang=(getattr(u, "language_code", None) or "en"),
            )
    except Exception:
        import logging
        logging.getLogger(__name__).debug("ensure_profile failed", exc_info=True)


# ✅ ВАЖНО: экспортируем именно usage_gate, потому что english_bot.py импортирует это имя
async def usage_gate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_countable_message(update):
        return

    await _ensure_profile(update, ctx)

    # не считаем ввод промокода на онбординге
    try:
        sess = _get_session(update)
        if sess.get("onboarding_stage") == "awaiting_promo":
            return
    except Exception:
        pass

    user_id = update.effective_user.id

    # 1) Любой активный доступ (premium/промо) — лимиты не применяем
    profile = get_profile(user_id)
    if has_unlimited_messages(profile):
        return

    # 2) Free: считаем лимит 15/день
    used = get_usage(user_id)
    lang = _ui_lang(update, ctx)

    limit_text = _offer_text("limit_reached", lang) or (
        "Лимит пробного дня достигнут." if lang == "ru" else "You’ve hit the daily trial limit."
    )
    reminder_text = _offer_text("reminder_after_10", lang) or (
        "Осталось 5 сообщений в пробном периоде." if lang == "ru" else "You’ve got 5 messages left on the trial."
    )

    msg = update.message or update.edited_message

    if used >= FREE_DAILY_LIMIT:
        hint = (
            "\n\n💡 Введите /promo для активации промокода и продолжения."
            if lang == "ru"
            else "\n\n💡 Enter /promo to activate a promo code and continue."
        )
        await msg.reply_text(limit_text + hint)
        raise ApplicationHandlerStop

    used = increment_usage(user_id)

    if used == REMIND_AFTER:
        hint = (
            "\n\n💡 Есть промокод? Введите /promo <код>."
            if lang == "ru"
            else "\n\n💡 Have a promo code? Use /promo <code>."
        )
        await msg.reply_text(reminder_text + hint)

    if used > FREE_DAILY_LIMIT:
        hint = (
            "\n\n💡 Введите /promo для активации промокода и продолжения."
            if lang == "ru"
            else "\n\n💡 Enter /promo to activate a promo code and continue."
        )
        await msg.reply_text(limit_text + hint)
        raise ApplicationHandlerStop
