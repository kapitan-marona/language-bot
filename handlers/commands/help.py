from __future__ import annotations
from datetime import datetime, timezone  # NEW
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from components.offer_texts import OFFER
from components.profile_db import get_user_profile
from components.usage_db import get_usage
from components.access import has_access
from components.i18n import get_ui_lang  # NEW


def _offer_text(key: str, lang: str) -> str:  # NEW: безопасно берём строку из OFFER с фолбэком
    d = OFFER.get(key) if isinstance(OFFER, dict) else None
    if not isinstance(d, dict):
        return ""
    if lang in d:
        return d[lang]
    return d.get("en") or d.get("ru") or next(iter(d.values()), "")


def _help_text(user_id: int, ui: str) -> str:
    used = get_usage(user_id)

    if has_access(user_id):
        header = _offer_text("help_premium_header", ui) or (  # NEW
            ("Премиум доступ" if ui == "ru" else "Premium access")
        )
        profile = get_user_profile(user_id) or {}
        exp = profile.get("premium_expires_at") or "—"
        # NEW: аккуратно парсим дату и форматируем
        until = "—"
        try:
            if exp and exp != "—":
                dt = datetime.fromisoformat(exp)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                until = dt.date().isoformat()
        except Exception:
            until = "—"

        card_tpl = _offer_text("premium_card", ui) or (  # NEW
            ("🎟 Премиум активен до {date}. Сообщения сегодня: {used}/∞"
             if ui == "ru"
             else "🎟 Premium active until {date}. Messages today: {used}/∞")
        )
        card = card_tpl.format(date=until, used=used)
    else:
        header = _offer_text("help_free_header", ui) or (  # NEW
            ("Бесплатный доступ" if ui == "ru" else "Free access")
        )
        card_tpl = _offer_text("free_card", ui) or (  # NEW
            ("🔓 Сообщения сегодня: {used}/15" if ui == "ru" else "🔓 Messages today: {used}/15")
        )
        card = card_tpl.format(used=used)

    # Список команд — все они зарегистрированы в english_bot.py
    # /start — запуск онбординга (через send_onboarding)
    # /reset — очистка сессии + онбординг
    # /buy — покупка через Stars (invoice)
    # /donate — поддержать проект (кнопка ведёт к htp_buy)
    # /promo — промокод
    # /teach, /glossary — режим корректировок
    common = _offer_text("help_body_common", ui) or (  # NEW
        ("Команды:\n"
         "/buy — купить доступ на 30 дней\n"
         "/donate — поддержать проект\n"
         "/promo — активировать промокод\n"
         "/lang — сменить язык интерфейса/практики\n"
         "/glossary — личные корректировки перевода")
        if ui == "ru" else
        ("Commands:\n"
         "/buy — get 30-day access\n"
         "/donate — support the project\n"
         "/promo — apply a promo code\n"
         "/lang — change interface/practice language\n"
         "/glossary — your translation corrections")
    )

    return f"*{header}*\n{card}\n\n{common}"  # CHANGED: header уже жирный


def _help_keyboard(ui: str, premium: bool) -> InlineKeyboardMarkup:
    # Все callback_data привязаны к существующим хендлерам:
    # open:settings -> handlers/callbacks/menu.menu_router => "/donate", "/promo", "/buy" и т.п.
    # htp_start     -> handlers/callbacks/how_to_pay_game.how_to_pay_entry (текстовая игра «Как оплатить?»)
    # htp_buy       -> handlers/callbacks/how_to_pay_game.how_to_pay_go_buy -> buy_command (invoice)
    rows = []

    # Настройки (внутреннее меню)
    rows.append([InlineKeyboardButton("⚙️ Settings" if ui == "en" else "⚙️ Настройки", callback_data="open:settings")])

    # Оплата
    buy_label = "Buy 30 days — 149 ⭐" if ui == "en" else "Купить 30 дней — 149 ⭐"
    how_label = "How to pay?" if ui == "en" else "Как оплатить?"
    rows.append([
        InlineKeyboardButton(buy_label, callback_data="htp_buy"),
        InlineKeyboardButton(how_label, callback_data="htp_start"),
    ])

    # Промокод и поддержка
    promo_label = "Promo code" if ui == "en" else "Промокод"
    donate_label = "Support" if ui == "en" else "Поддержать"
    rows.append([
        InlineKeyboardButton(promo_label, callback_data="open:promo"),
        InlineKeyboardButton(donate_label, callback_data="open:donate"),
    ])

    # Быстрые команды как кнопки (удобно на мобилках)
    rows.append([
        InlineKeyboardButton("/teach", callback_data="open:teach"),
        InlineKeyboardButton("/glossary", callback_data="open:glossary"),
    ])

    # Прямые команды / ссылки бот-команд — остаются в тексте (см. _help_text)
    return InlineKeyboardMarkup(rows)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, context)  # NEW
    user_id = update.effective_user.id
    is_premium = has_access(user_id)

    text = _help_text(user_id, ui)
    kb = _help_keyboard(ui, is_premium)

    # В /help команда приходит как message
    await update.message.reply_markdown(text, reply_markup=kb)
