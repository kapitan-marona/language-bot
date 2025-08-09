# handlers/commands/help.py
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import ContextTypes
from components.profile_db import get_user_profile


def _ui_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Определяем язык интерфейса пользователя (ru/en)."""
    return (context.user_data or {}).get("ui_lang", "ru")


def _lang_human_name(code: str) -> str:
    """Человекочитаемое имя изучаемого языка."""
    return {"en": "English", "es": "Español", "de": "Deutsch"}.get(code, code.upper())


def _extract_promo(profile: dict | None) -> tuple[str | None, str | None]:
    """Достаём промокод и срок: поддерживаем p['promo']={code,expires} и плоские поля."""
    p = profile or {}
    promo = p.get("promo")
    code = expires = None
    if isinstance(promo, dict):
        code = promo.get("code")
        expires = promo.get("expires")
    else:
        code = p.get("promo_code") or p.get("promoCode")
        expires = p.get("promo_expires") or p.get("promoExpires")
    return code, expires


def _help_text_ru(profile: dict | None) -> str:
    p = profile or {}
    lang_code = p.get("target_lang", "en")
    level = p.get("level", "B1")
    style = {"casual": "Разговорный", "business": "Деловой"}.get(
        p.get("style", "casual"), p.get("style", "casual")
    )
    code, expires = _extract_promo(p)
    promo_line = (
        f"🎟️ Промокод: {code} — до {expires}" if (code and expires) else "🎟️ Промокод: не указан"
    )
    return (
        "📖 Помощь уже здесь!\n\n"
        f"Текущие настройки: язык — {_lang_human_name(lang_code)}, уровень — {level}, стиль — {style}.\n"
        f"{promo_line}\n\n"
        "⚙️ <b>Настройки</b> — /settings\n"
        "• Меняй язык, уровень и стиль общения.\n\n"
        "🎛 <b>Режим</b> — /mode\n"
        "• Выбирай, как будем общаться.\n\n"
        "🎟️ <b>Промокод</b> — /promo\n"
        "• Узнай срок действия кода.\n\n"
        "💬 <b>Обратная связь</b>\n"
        "• Напиши разработчику."
    )


def _help_text_en(profile: dict | None) -> str:
    p = profile or {}
    lang_code = p.get("target_lang", "en")
    level = p.get("level", "B1")
    style = {"casual": "Casual", "business": "Business"}.get(
        p.get("style", "casual"), p.get("style", "casual")
    )
    code, expires = _extract_promo(p)
    promo_line = (
        f"🎟️ Promo code: {code} — until {expires}" if (code and expires) else "🎟️ Promo code: none"
    )
    return (
        "📖 Help is already here!\n\n"
        f"Current: language — {_lang_human_name(lang_code)}, level — {level}, style — {style}.\n"
        f"{promo_line}\n\n"
        "⚙️ <b>Settings</b> — /settings\n"
        "• Change language, level, and chat style.\n\n"
        "🎛 <b>Mode</b> — /mode\n"
        "• Choose how we chat.\n\n"
        "🎟️ <b>Promo code</b> — /promo\n"
        "• Check your code expiry.\n\n"
        "💬 <b>Feedback</b>\n"
        "• Message the developer."
    )


def _inline_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Инлайн-клавиатура для меню помощи (без ReplyKeyboard)."""
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


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /help: показывает карточку и убирает висящую ReplyKeyboard."""
    if update.message:
        try:
            await update.message.reply_text("", reply_markup=ReplyKeyboardRemove())
        except Exception:
            pass

    lang = _ui_lang(context)
    user_id = update.effective_user.id if update and update.effective_user else None
    profile = get_user_profile(user_id) if user_id else {}

    # надёжно определяем изучаемый язык (из профиля или user_data)
    profile["target_lang"] = profile.get("target_lang") or (context.user_data or {}).get("language", "en")

    text = _help_text_ru(profile) if lang == "ru" else _help_text_en(profile)

    if update.message:
        await update.message.reply_html(text, reply_markup=_inline_keyboard(lang))
    else:
        await update.effective_chat.send_message(text, reply_markup=_inline_keyboard(lang))


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки меню помощи."""
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
        # локальный импорт исключает циклическую зависимость при запуске
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
        # показываем статус промокода отдельным сообщением (не редактируя /help)
        profile = get_user_profile(q.from_user.id) or {}
        code, expires = _extract_promo(profile)
        if code and expires:
            text = (
                f"🎟️ Твой промокод: {code}\nДействует до {expires}."
                if lang == "ru"
                else f"🎟️ Your promo code: {code}\nValid until {expires}."
            )
        else:
            text = (
                "🎟️ Похоже, кода пока нет — не страшно! Пришлёшь, как будет 😉"
                if lang == "ru"
                else "🎟️ Looks like we don’t have a code yet — no rush! Send it when you do 😉"
            )
        await context.bot.send_message(chat_id, text)
        return
