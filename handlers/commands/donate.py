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
        btns = [[InlineKeyboardButton("Оформить доступ (/buy)", callback_data="open:sub")]]
    else:
        text = (
            "Thanks for supporting the project! 🙌\n\n"
            "You can support via Telegram Stars.\n"
            "Tap /buy — 30 days Premium for 149 ⭐ (this supports the project too).\n\n"
            "If you see *Get Stars* — top up ⭐ and return to the invoice."
        )
        btns = [[InlineKeyboardButton("Get Premium (/buy)", callback_data="open:sub")]]

    await update.effective_message.reply_text(text, reply_markup=InlineKeyboardMarkup(btns))
