from __future__ import annotations
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from state.session import user_sessions
from components.i18n import get_ui_lang
from components.payments import send_donation_invoice

logger = logging.getLogger(__name__)

# Диапазон допустимых сумм доната в звёздах
MIN_DONATE = 1
MAX_DONATE = 10_000

# Пресеты сумм (по запросу)
_PRESETS = [10, 20, 50]

# До 5 цифр — хватит для 10_000
_AMOUNT_RE = re.compile(r"^\s*(\d{1,5})\s*$")

def _donate_keyboard(ui: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(str(p), callback_data=f"DONATE:{p}") for p in _PRESETS]]
    rows.append([InlineKeyboardButton("Другая сумма" if ui == "ru" else "Other amount",
                                      callback_data="DONATE:CUSTOM")])
    rows.append([InlineKeyboardButton("❌ Отмена" if ui == "ru" else "❌ Cancel",
                                      callback_data="DONATE:CANCEL")])
    return InlineKeyboardMarkup(rows)

async def donate_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /donate [amount]
    Пример: /donate 50 — сразу счёт на 50⭐
    Без суммы — показываем клавиатуру пресетов + Другая сумма + Отмена.
    """
    ui = get_ui_lang(update, ctx)
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    sess.pop("donate_waiting_amount", None)  # сбросим возможный флаг

    # Если указан аргумент — пытаемся сразу выставить счёт
    args = getattr(ctx, "args", None) or []
    if args:
        m = _AMOUNT_RE.match(" ".join(args))
        if not m:
            text = ("Укажи сумму как число, например: /donate 50"
                    if ui == "ru" else
                    "Provide the amount as a number, e.g.: /donate 50")
            await update.message.reply_text(text)
            return
        amount = int(m.group(1))
        if amount < MIN_DONATE or amount > MAX_DONATE:
            text = (f"Сумма должна быть от {MIN_DONATE} до {MAX_DONATE}⭐"
                    if ui == "ru" else
                    f"Amount must be between {MIN_DONATE} and {MAX_DONATE}⭐")
            await update.message.reply_text(text)
            return
        await send_donation_invoice(update, ctx, amount)
        return

    # Иначе — показываем пресеты
    text = ("Поддержи проект любой суммой в звёздах ⭐\n"
            "Выбери сумму или укажи другую." if ui == "ru" else
            "Support the project with any amount of Stars ⭐\n"
            "Pick an amount or enter a custom one.")
    await update.message.reply_text(text, reply_markup=_donate_keyboard(ui))

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Колбэки DONATE:<...>
    DONATE:<N>      — сразу инвойс
    DONATE:CUSTOM   — просим ввести число, ждём сообщение
    DONATE:CANCEL   — отменяем сценарий доната
    """
    q = update.callback_query
    if not q or not q.data:
        return

    ui = get_ui_lang(update, ctx)
    chat_id = q.message.chat.id
    sess = user_sessions.setdefault(chat_id, {})
    data = q.data

    # Отмена
    if data == "DONATE:CANCEL":
        sess.pop("donate_waiting_amount", None)
        try:
            await q.answer("❌")
        except Exception:
            pass
        text = "Отменил, всё ок 👍" if ui == "ru" else "Cancelled, no worries 👍"
        # заменим клавиатуру, чтобы не жали старые кнопки
        await q.edit_message_text(text)
        return

    # Другая сумма — ждём число
    if data == "DONATE:CUSTOM":
        sess["donate_waiting_amount"] = True
        try:
            await q.answer("…")
        except Exception:
            pass
        ask = ("Введи сумму числом (1–10000). Или отправь /donate 50."
               if ui == "ru" else
               "Send the amount as a number (1–10000). Or use /donate 50.")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена" if ui == "ru" else "❌ Cancel",
                                                         callback_data="DONATE:CANCEL")]])
        await q.edit_message_text(ask, reply_markup=kb)
        return

    # DONATE:<N>
    if data.startswith("DONATE:"):
        try:
            amount = int(data.split(":", 1)[1])
        except Exception:
            await q.answer("⚠️")
            return
        if amount < MIN_DONATE or amount > MAX_DONATE:
            await q.answer("⚠️")
            warn = (f"Сумма должна быть от {MIN_DONATE} до {MAX_DONATE}⭐"
                    if ui == "ru" else
                    f"Amount must be between {MIN_DONATE} and {MAX_DONATE}⭐")
            await q.edit_message_text(warn)
            return
        try:
            await q.answer("✅")
        except Exception:
            pass
        # Можно оставить сообщение с кнопками — инвойс придёт отдельным сообщением
        await send_donation_invoice(update, ctx, amount)
        return

async def on_amount_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает сообщение с числом, если до этого выбрали «Другая сумма».
    Если флаг ожидания не выставлен — молча ничего не делаем (дадим пройти другим хендлерам).
    """
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    if not sess.get("donate_waiting_amount"):
        return  # не наш кейс — передадим управление остальным

    ui = get_ui_lang(update, ctx)
    text = (update.message.text or "").strip()
    m = _AMOUNT_RE.match(text)
    if not m:
        warn = ("Укажи сумму как число, например 50. Или /donate 50."
                if ui == "ru" else
                "Provide the amount as a number, e.g. 50. Or /donate 50.")
        await update.message.reply_text(warn)
        return

    amount = int(m.group(1))
    if amount < MIN_DONATE or amount > MAX_DONATE:
        warn = (f"Сумма должна быть от {MIN_DONATE} до {MAX_DONATE}⭐"
                if ui == "ru" else
                f"Amount must be between {MIN_DONATE} and {MAX_DONATE}⭐")
        await update.message.reply_text(warn)
        return

    # Снимаем флаг ожидания и отправляем инвойс
    sess.pop("donate_waiting_amount", None)
    await send_donation_invoice(update, ctx, amount)
