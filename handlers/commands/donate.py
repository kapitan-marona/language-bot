from __future__ import annotations
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

async def donate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("ui_lang", "ru")
    if lang == "ru":
        text = (
            "Спасибо, что хочешь поддержать проект! 🙌\n\n"
            "Сейчас поддержка возможна через Telegram Stars.\n"
            "Нажми /buy — оформи доступ на 30 дней за 149 ⭐ (это тоже поддержка).\n\n"
            "Если увидишь кнопку *Get Stars* — пополни ⭐ и вернись к счёту."
        )
        btns = [[InlineKeyboardButton("Оформить доступ (/buy)", callback_data="htp_buy")]]
    else:
        text = (
            "Thanks for supporting the project! 🙌\n\n"
            "Support is available via Telegram Stars.\n"
            "Tap /buy — get 30-day access for 149 ⭐ (that supports the project, too).\n\n"
            "If you see *Get Stars*, top up ⭐ and return to the invoice."
        )
        btns = [[InlineKeyboardButton("Proceed to /buy", callback_data="htp_buy")]]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(btns))
