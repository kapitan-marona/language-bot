from __future__ import annotations
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from components.i18n import get_ui_lang
from components.profile_db import get_user_profile
from components.usage_db import get_usage
from components.access import has_access

FREE_DAILY_LIMIT = 15  # для отображения в free-карточке

# --------- Тексты справки (без /teach) ---------
HELP_BODY_RU = (
    "🆘 Команды и инструкции\n\n"
    "Доступные команды:\n"
    "• /help — показать это сообщение\n"
    "\n"
    "• /start — начать сначала (онбординг)\n"
    "• /settings — открыть настройки (язык, уровень, стиль)\n"
    "• /language — сменить язык общения\n"
    "• /level — сменить уровень (A0–C2)\n"
    "• /style — сменить стиль общения\n"
    "• /buy — купить доступ\n"
    "• /promo — ввести промокод\n"
    "• /donate — поддержать проект\n"
    "\n"
    "Советы по общению с Мэттом:\n"
    "• Мэтт — собеседник. Он не видит ваши настройки и оплату. Фразы вроде «поменяй уровень/язык/стиль» не сработают — "
    "для этого есть команды: /settings, /language, /level, /style; оплата — /buy, /donate и /promo для промокода.\n"
    "• Можно общаться голосом или текстом. Если хочешь услышать, как что-то звучит, напиши «озвучь» — "
    "Мэтт пришлёт аудио (разовая озвучка, режим не меняется).\n"
    "• Подсказка: в /settings изменения применяются сразу после выбора — можно просто продолжать диалог.\n"
)

HELP_BODY_EN = (
    "🆘 Commands & Instructions\n\n"
    "Available commands:\n"
    "• /help — show this message\n"
    "\n"
    "• /start — start over (onboarding)\n"
    "• /settings — open settings (language, level, style)\n"
    "• /language — change the chat language\n"
    "• /level — change the level (A0–C2)\n"
    "• /style — change the conversation style\n"
    "• /buy — purchase access\n"
    "• /promo — enter a promo code\n"
    "• /donate — support the project\n"
    "\n"
    "Tips for chatting with Matt:\n"
    "• Matt is a conversation partner. He doesn’t see your settings or billing. Saying “change my level/language/style” won’t work — "
    "use /settings, /language, /level, /style. Payments/promos go through /buy, /donate, and /promo.\n"
    "• You can chat in voice or text. If you want to hear how something sounds, say “voice it” — "
    "Matt will send a one-off audio reply (it doesn’t switch the mode).\n"
    "• Pro tip: in /settings, changes apply immediately after selection — just keep chatting.\n"
)

def _kb(ui: str) -> InlineKeyboardMarkup:
    buy_label = "Buy 30 days — 149 ⭐" if ui == "en" else "Купить 30 дней — 149 ⭐"
    how_label = "How to pay?" if ui == "en" else "Как оплатить?"
    settings_label = "⚙️ Settings" if ui == "en" else "⚙️ Настройки"
    promo_label = "Promo code" if ui == "en" else "Промокод"
    donate_label = "Support" if ui == "en" else "Поддержать"

    rows = [
        [InlineKeyboardButton(settings_label, callback_data="open:settings")],
        [
            InlineKeyboardButton(buy_label, callback_data="htp_buy"),
            InlineKeyboardButton(how_label, callback_data="htp_start"),
        ],
        [
            InlineKeyboardButton(promo_label, callback_data="open:promo"),
            InlineKeyboardButton(donate_label, callback_data="open:donate"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ui = get_ui_lang(update, context)
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # БД/аккаунт — асинхронно через thread pool
    is_premium, used, profile = await asyncio.gather(
        asyncio.to_thread(has_access, user_id),
        asyncio.to_thread(get_usage, user_id),
        asyncio.to_thread(get_user_profile, user_id),
    )
    profile = profile or {}

    # Карточка статуса (динамика как в старой версии)
    if ui == "ru":
        if is_premium:
            until = (profile.get("premium_expires_at") or "—")
            header = f"*🌟 Премиум активен*\nДоступ до: `{until}`"
            card = ""
        else:
            header = "*🆓 Бесплатный режим*"
            card = f"\nСегодня использовано: *{used}/{FREE_DAILY_LIMIT}*"
        body = HELP_BODY_RU
    else:
        if is_premium:
            until = (profile.get("premium_expires_at") or "—")
            header = f"*🌟 Premium is active*\nAccess until: `{until}`"
            card = ""
        else:
            header = "*🆓 Free plan*"
            card = f"\nUsed today: *{used}/{FREE_DAILY_LIMIT}*"
        body = HELP_BODY_EN

    text = f"{header}{card}\n\n{body}"

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=_kb(ui),
    )
