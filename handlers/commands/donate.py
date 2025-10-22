# handlers/commands/donate.py
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes, ApplicationHandlerStop
from components.i18n import get_ui_lang
from components.payments import send_donation_invoice

async def donate_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Старт доната. Просим ввести сумму звёзд.
    """
    ui = get_ui_lang(update, ctx)
    ctx.user_data["donate_wait_amount"] = True  # >>> ADDED
    if ui == "ru":
        await update.message.reply_text("💫 Введите сумму в звёздах (например, 10 или 100).")
    else:
        await update.message.reply_text("💫 Enter the amount in Stars (e.g. 10 or 100).")
    raise ApplicationHandlerStop  # >>> ADDED

async def on_amount_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает число, введённое после /donate.
    """
    text = (update.message.text or "").strip()
    # если это не целое число — не наш хендлер
    if not text.isdigit():
        return

    amount = int(text)
    if amount <= 0 or amount > 100000:
        ui = get_ui_lang(update, ctx)
        await update.message.reply_text("⚠️ Некорректная сумма." if ui == "ru" else "⚠️ Invalid amount.")
        ctx.user_data.pop("donate_wait_amount", None)  # >>> ADDED
        raise ApplicationHandlerStop  # >>> ADDED

    # отправляем счёт в Stars
    await send_donation_invoice(update, ctx, amount)

    # снимаем флаг «жду сумму»
    ctx.user_data.pop("donate_wait_amount", None)  # >>> ADDED

    # и обрубаем дальнейшую обработку этого сообщения
    raise ApplicationHandlerStop  # >>> ADDED
