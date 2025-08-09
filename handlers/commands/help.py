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
        "• Узнай, сколько ещё действует твой промокод и не забыл ли ты его ввести.\n\n"
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
        "• Check how long your promo is valid and whether you’ve added it.\n\n"
        "💬 <b>Feedback</b>\n"
        "• Ask Matt who created him — he’ll send a link to the developer for feedback or collaboration.\n\n"
        "…or simply call /help anytime 😊"
    )


def _inline_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Инлайн-кнопки (без ReplyKeyboard, чтобы ничего не подставлялось в поле ввода)."""
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


# ---------- Форматирование промокода ----------

def _format_promo_status_from_profile(p: dict, ui: str) -> str:
    """
    Ожидаем поля профиля:
      promo_code_used: str | None
      promo_type: 'timed' | 'permanent' | 'english_only' | None
      promo_activated_at: ISO-строка (UTC) | None
      promo_days: int | None
    """
    code = p.get("promo_code_used")
    ptype = p.get("promo_type")
    act = p.get("promo_activated_at")
    days = p.get("promo_days")

    if not code or not ptype:
        return "🎟️ Кода пока нет — введи через /promo." if ui == "ru" else "🎟️ No code yet — add via /promo."

    if ptype == "permanent":
        return (f"🎟️ Промокод {code}: бессрочно.") if ui == "ru" else (f"🎟️ Promo {code}: permanent.")

    if ptype == "english_only":
        return (
            f"🎟️ Промокод {code}: бессрочный, действует только для английского языка."
            if ui == "ru"
            else f"🎟️ Promo {code}: permanent, English only."
        )

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
            # русская форма без склонений — коротко и понятно
            return (
                f"🎟️ Промокод активен: осталось {left} дн."
                if ui == "ru"
                else f"🎟️ Promo active: {left} days left."
            )
        except Exception:
            return "🎟️ Промокод активирован (временной)." if ui == "ru" else "🎟️ Promo active (timed)."

    return "🎟️ Промокод активирован." if ui == "ru" else "🎟️ Promo active."


# ---------- Команды / колбэки ----------

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает карточку помощи и прячет зависшую ReplyKeyboard (если была)."""
    if update.message:
        # пустую строку Telegram иногда ругает — используем невидимый символ
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
        # показываем отдельным сообщением, меню помощи не трогаем
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
