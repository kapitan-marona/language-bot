# handlers/commands/help.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import ContextTypes

from components.profile_db import get_user_profile


def _ui_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Язык интерфейса (по умолчанию RU)."""
    return (context.user_data or {}).get("ui_lang", "ru")


# ---------- Текстовые блоки ----------

def _help_text_ru() -> str:
    return (
        "✨ Помощь уже здесь!\n\n"
        "⚙️ <b>Настройки</b> — /settings\n"
        "• Меняй язык, уровень и стиль общения по прямой команде.\n\n"
        "🎛 <b>Режим</b> — /mode\n"
        "• Меняй формат общения с текстового на голосовой и обратно в любой момент. "
        "Можно просто написать «текст» или «голос», и Мэтт поймёт.\n\n"
        "🎟️ <b>Промокод</b> — /promo\n"
        "• Скоро тут будет подсказка по использованию промокодов.\n\n"
        "💬 <b>Обратная связь</b>\n"
        "• Спроси у Мэтта, кто его создал — он даст ссылку на разработчика. "
        "Туда можно написать отзыв или предложить сотрудничество.\n\n"
        "…или просто зови /help в любой момент 😊"
    )


def _help_text_en() -> str:
    return (
        "✨ Help is here!\n\n"
        "⚙️ <b>Settings</b> — /settings\n"
        "• Change your language, level, and chat style.\n\n"
        "🎛 <b>Mode</b> — /mode\n"
        "• Switch between text and voice anytime. You can just type “text” or “voice” — Matt will get it.\n\n"
        "🎟️ <b>Promo code</b> — /promo\n"
        "• Soon there will be a hint about using promo codes.\n\n"
        "💬 <b>Feedback</b>\n"
        "• Ask Matt who created him — he’ll send a link to the developer for feedback or collaboration.\n\n"
        "…or simply call /help anytime 😊"
    )


def _inline_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Инлайн-кнопки (без ReplyKeyboard)."""
    btn_settings = InlineKeyboardButton(
        text=("⚙️ Настройки" if lang == "ru" else "⚙️ Settings"),
        callback_data="HELP:OPEN:SETTINGS",
    )
    btn_mode = InlineKeyboardButton(
        text=("🎛 Режим" if lang == "ru" else "🎛 Mode"),
        callback_data="HELP:OPEN:MODE",
    )
    btn_promo = InlineKeyboardButton(
        text=("🎟️ Промокод" if lang == "ru" else "🎟️ Promo"),
        callback_data="HELP:OPEN:PROMO",
    )
    btn_contact = InlineKeyboardButton(
        text=("💬✨ Написать разработчику" if lang == "ru" else "💬✨ Message the developer"),
        url="https://t.me/marrona",
    )
    return InlineKeyboardMarkup([[btn_settings, btn_mode, btn_promo], [btn_contact]])


# ---------- Промокоды (новый + старый формат) ----------

def _format_promo_status_from_profile(p: dict, ui: str) -> str:
    """
    Поддерживает новый и старый форматы профиля:
      Новый: promo_code_used, promo_type, promo_activated_at (ISO, UTC), promo_days
      Старый: promo={code,expires} ИЛИ promo_code (+ promo_expires)
    """
    # Новый формат
    code = p.get("promo_code_used")
    ptype = p.get("promo_type")
    act = p.get("promo_activated_at")
    days = p.get("promo_days")

    # Старый формат (fallback)
    if not code or not ptype:
        legacy = p.get("promo")
        if isinstance(legacy, dict):
            lcode = legacy.get("code")
            lexp = legacy.get("expires")
            if lcode and lexp:
                return (f"🎟️ Промокод: {lcode} — до {lexp}"
                        if ui == "ru" else f"🎟️ Promo code: {lcode} — until {lexp}")
        lcode = p.get("promo_code") or p.get("promoCode")
        lexp = p.get("promo_expires") or p.get("promoExpires")
        if lcode and lexp:
            return (f"🎟️ Промокод: {lcode} — до {lexp}"
                    if ui == "ru" else f"🎟️ Promo code: {lcode} — until {lexp}")

    if not code or not ptype:
        return "🎟️ Кода пока нет — введи через /promo." if ui == "ru" else "🎟️ No code yet — add via /promo."

    if ptype == "permanent":
        return (f"🎟️ Промокод {code}: бессрочно."
                if ui == "ru" else f"🎟️ Promo {code}: permanent.")

    if ptype == "english_only":
        return ("🎟️ Промокод {0}: бессрочный, действует только для английского языка."
                .format(code) if ui == "ru" else f"🎟️ Promo {code}: permanent, English only.")

    if ptype == "timed" and act and days:
        try:
            dt = datetime.fromisoformat(act)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            end = dt + timedelta(days=int(days))
            left = (end.date() - datetime.now(timezone.utc).date()).days
            if left < 0:
                return "🎟️ Промокод истёк." if ui == "ru" else "🎟️ Promo expired."
            if left == 0:
                return "🎟️ Промокод истекает сегодня!" if ui == "ru" else "🎟️ Promo expires today!"
            return (f"🎟️ Промокод активен: осталось {left} дн."
                    if ui == "ru" else f"🎟️ Promo active: {left} days left.")
        except Exception:
            return "🎟️ Промокод активирован (временной)." if ui == "ru" else "🎟️ Promo active (timed)."

    return "🎟️ Промокод активирован." if ui == "ru" else "🎟️ Promo active."


# ---------- Команды / колбэки ----------

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает карточку помощи и прячет зависшую ReplyKeyboard (если была)."""
    if update.message:
        try:
            await update.message.reply_text("\u2063", reply_markup=ReplyKeyboardRemove())
        except Exception:
            pass

    lang = _ui_lang(context)
    text = _help_text_ru() if lang == "ru" else _help_text_en()

    if update.message:
        await update.message.reply_html(text, reply_markup=_inline_keyboard(lang))
    else:
        await update.effective_chat.send_message(text, reply_markup=_inline_keyboard(lang))


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик инлайн-кнопок из /help (паттерн ^HELP:OPEN:)."""
    q = update.callback_query
    if not q:
        return
    await q.answer()

    data = (q.data or "")
    if not data.startswith("HELP:OPEN:"):
        return

    action = data.split(":", 2)[-1]
    chat_id = q.message.chat.id
    lang = _ui_lang(context)

    if action == "SETTINGS":
        # локальный импорт, чтобы избежать циклических зависимостей при старте
        from handlers.settings import cmd_settings
        return await cmd_settings(update, context)

    if action == "MODE":
        try:
            from components.mode import get_mode_keyboard
            current_mode = context.user_data.get("mode", "text")
            kb = get_mode_keyboard(current_mode, lang)
            await context.bot.send_message(
                chat_id,
                "Выбери, как будем общаться:" if lang == "ru" else "Choose how we chat:",
                reply_markup=kb,
            )
        except Exception:
            await context.bot.send_message(chat_id, "Отправь /mode" if lang == "ru" else "Send /mode")
        return

    if action == "PROMO":
        profile = get_user_profile(chat_id) or {}
        line = _format_promo_status_from_profile(profile, lang)
        await context.bot.send_message(chat_id, line)
        return
