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
    return (context.user_data or {}).get("ui_lang", "ru")


def _help_text_ru(profile: dict | None) -> str:
    p = profile or {}
    lang = p.get("target_lang", "en")
    level = p.get("level", "B1")
    style = {"casual": "Разговорный", "business": "Деловой"}.get(
        p.get("style", "casual"), p.get("style", "casual")
    )
    promo = p.get("promo")
    promo_line = (
        f"🎟️ Промокод: {promo.get('code')} — до {promo.get('expires')}"
        if isinstance(promo, dict) and promo.get("code") and promo.get("expires")
        else "🎟️ Промокод: не указан"
    )
    return (
        "Помощь уже здесь!\n\n"
        f"Текущие настройки: язык — {lang.upper()}, уровень — {level}, стиль — {style}.\n"
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
    lang = p.get("target_lang", "en")
    level = p.get("level", "B1")
    style = {"casual": "Casual", "business": "Business"}.get(
        p.get("style", "casual"), p.get("style", "casual")
    )
    promo = p.get("promo")
    promo_line = (
        f"🎟️ Promo code: {promo.get('code')} — until {promo.get('expires')}"
        if isinstance(promo, dict) and promo.get("code") and promo.get("expires")
        else "🎟️ Promo code: none"
    )
    return (
        "Help is already here!\n\n"
        f"Current: language — {lang.upper()}, level — {level}, style — {style}.\n"
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
    # Кнопки через callback_data — срабатывают сразу и НЕ подставляют текст в поле ввода
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
    # Принудительно уберём любую ReplyKeyboard, если она висит
    if update.message:
        try:
            await update.message.reply_text("", reply_markup=ReplyKeyboardRemove())
        except Exception:
            pass

    lang = _ui_lang(context)
    user_id = update.effective_user.id if update and update.effective_user else None
    profile = get_user_profile(user_id) if user_id else None
    text = _help_text_ru(profile) if lang == "ru" else _help_text_en(profile)

    if update.message:
        await update.message.reply_html(text, reply_markup=_inline_keyboard(lang))
    else:
        await update.effective_chat.send_message(text, reply_markup=_inline_keyboard(lang))


# Callback для инлайн-кнопок из /help
async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        return await cmd_settings(update, context)

    if action == "PROMO":
        # Покажем статус промокода отдельным сообщением
        profile = get_user_profile(q.from_user.id)
        promo = (profile or {}).get("promo")
        if isinstance(promo, dict) and promo.get("code") and promo.get("expires"):
            text = (
                f"🎟️ Твой промокод: {promo['code']}\n"
                f"Действует до {promo['expires']}." if lang == "ru"
                else f"🎟️ Your promo code: {promo['code']}\n"
                     f"Valid until {promo['expires']}."
            )
        else:
            text = (
                "🎟️ Похоже, кода пока нет — не страшно! Пришлёшь, как будет 😉" if lang == "ru"
                else "🎟️ Looks like we don’t have a code yet — no rush! Send it when you do 😉"
            )
        await context.bot.send_message(chat_id, text)
        return

