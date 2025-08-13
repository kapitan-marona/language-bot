from __future__ import annotations
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from components.offer_texts import OFFER
from components.profile_db import get_user_profile
from components.usage_db import get_usage
from components.access import has_access


from components.profile_db import get_user_profile

def _ui_lang(ctx: ContextTypes.DEFAULT_TYPE, user_id: int | None = None) -> str:
    ui = ctx.user_data.get('ui_lang') if getattr(ctx, 'user_data', None) else None
    if ui:
        return ui
    if user_id is None:
        return 'ru'
    prof = get_user_profile(user_id) or {}
    ui = prof.get('interface_lang', 'ru')
    try:
        ctx.user_data['ui_lang'] = ui
    except Exception:
        pass
    return ui


def _help_text(user_id: int, ui: str) -> str:
    used = get_usage(user_id)
    if has_access(user_id):
        header = OFFER["help_premium_header"][ui]
        card = OFFER["premium_card"][ui].format(date=(get_user_profile(user_id) or {}).get("premium_expires_at", "—"), used=used)
    else:
        header = OFFER["help_free_header"][ui]
        card = OFFER["free_card"][ui].format(used=used)

    # Список команд — все они зарегистрированы в english_bot.py
    # /start — запуск онбординга (через send_onboarding)
    # /reset — очистка сессии + онбординг
    # /buy — покупка через Stars (invoice)
    # /donate — поддержать проект (кнопка ведёт к htp_buy)
    # /promo — промокод
    # /teach, /glossary — режим корректировок
    common = OFFER["help_body_common"][ui]
    return f"*{header}*\n{card}\n\n{common}"


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
    user_id = update.effective_user.id
    ui = _ui_lang(context, user_id)
    is_premium = has_access(user_id)

    text = _help_text(user_id, ui)
    kb = _help_keyboard(ui, is_premium)

    # В /help команда приходит как message
    await update.message.reply_markdown(text, reply_markup=kb)
