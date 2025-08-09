# handlers/commands/help.py
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes


def _ui_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return (context.user_data or {}).get("ui_lang", "ru")


def _help_text_ru() -> str:
    return (
        "Помощь уже здесь!.\n\n"
        "⚙️ <b>Настройки</b> — /settings\n"
        "• Меняй язык, уровень и стиль общения.\n\n"
        "🎛 <b>Режим</b> — /mode\n"
        "• Выбирай, как будем общаться.\n\n"
        "🎟️ <b>Промокод</b> — /promo\n"
        "• Узнай срок действия кода.\n\n"
        "💬 <b>Обратная связь</b>\n"
        "• Напиши разработчику."
    )


def _help_text_en() -> str:
    return (
        "Help is already here!.\n\n"
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
    # Кнопки без ReplyKeyboard: заполняем поле ввода с командами через switch_inline_query_current_chat
    btn_settings = InlineKeyboardButton(
        text=("⚙️ Настройки" if lang == "ru" else "⚙️ Settings"),
        switch_inline_query_current_chat="/settings",
    )
    btn_mode = InlineKeyboardButton(
        text=("🎛 Режим" if lang == "ru" else "🎛 Mode"),
        switch_inline_query_current_chat="/mode",
    )
    btn_promo = InlineKeyboardButton(
        text=("🎟️ Промокод" if lang == "ru" else "🎟️ Promo"),
        switch_inline_query_current_chat="/promo",
    )
    btn_contact = InlineKeyboardButton(
        text=("💬✨ Написать разработчику" if lang == "ru" else "💬✨ Message the developer"),
        url="https://t.me/marrona",
    )
    return InlineKeyboardMarkup([[btn_settings, btn_mode, btn_promo], [btn_contact]])


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _ui_lang(context)
    text = _help_text_ru() if lang == "ru" else _help_text_en()

    if update.message:
        await update.message.reply_html(text, reply_markup=_inline_keyboard(lang))
    else:
        await update.effective_chat.send_message(text, reply_markup=_inline_keyboard(lang))
