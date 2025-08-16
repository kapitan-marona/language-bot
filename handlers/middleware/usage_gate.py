from __future__ import annotations
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

def _ui_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:  # CHANGED: через общий резолвер
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
    # NEW: пока активна пауза (режим /teach), ничего не считаем и не блокируем
    if ctx.chat_data.get("dialog_paused"):
        return

    if not _is_countable_message(update):
        return

    # NEW: не считаем и не блокируем ввод промокода на онбординге
    try:
        chat_id = update.effective_chat.id
        sess = user_sessions.get(chat_id, {}) or {}
        if sess.get("onboarding_stage") == "awaiting_promo":
            return
    except Exception:
        pass

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
    lang = _ui_lang(update, ctx)  # CHANGED

    # Достаем тексты OFFER безопасно
    limit_text = _offer_text("limit_reached", lang) or (
        "Лимит пробного дня достигнут." if lang == "ru" else "You’ve hit the daily trial limit."
    )  # NEW
    reminder_text = _offer_text("reminder_after_10", lang) or (
        "Осталось 5 сообщений в пробном периоде." if lang == "ru" else "You’ve got 5 messages left on the trial."
    )  # NEW

    if used >= FREE_DAILY_LIMIT:
        hint = ("\n\n💡 Введите /promo для активации промокода и продолжения."
                if lang == "ru"
                else "\n\n💡 Enter /promo to activate a promo code and continue.")
        await (update.message or update.edited_message).reply_text(limit_text + hint)
        raise ApplicationHandlerStop

    used = increment_usage(user_id)

    if used == REMIND_AFTER:
        # NEW: добавим мягкий хинт про /promo и тут тоже
        hint = ("\n\n💡 Есть промокод? Введите /promo <код>."
                if lang == "ru"
                else "\n\n💡 Have a promo code? Use /promo <code>.")
        await (update.message or update.edited_message).reply_text(reminder_text + hint)

    if used > FREE_DAILY_LIMIT:
        hint = ("\n\n💡 Введите /promo для активации промокода и продолжения."
                if lang == "ru"
                else "\n\n💡 Enter /promo to activate a promo code and continue.")
        await (update.message or update.edited_message).reply_text(limit_text + hint)
        raise ApplicationHandlerStop
