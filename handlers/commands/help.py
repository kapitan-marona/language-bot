from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes

from components.i18n import get_ui_lang

# Короткая, актуальная справка без отключённых функций
HELP_TEXT_RU = (
    "🤖 *Помощь*\n\n"
    "Основные команды:\n"
    "• /start — начать или перезапустить онбординг\n"
    "• /settings — язык, уровень, стиль, режим вывода\n"
    "• /translator_on — включить режим переводчика\n"
    "• /translator_off — выйти из режима переводчика\n"
    "• /privacy — политика конфиденциальности\n"
    "• /delete_me — удалить мои данные\n\n"
    "Оплата и промо:\n"
    "• /buy — оформить подписку или пакет\n"
    "• /promo — активировать промокод\n"
    "• /donate — поддержать проект\n"
    "• /stars — оформить через Telegram Stars\n\n"
    "Быстрые настройки (дублируют /settings):\n"
    "• /language — сменить язык изучения\n"
    "• /level — сменить уровень (A0–C2)\n"
    "• /style — переключить стиль (Разговорный/Деловой)\n\n"
    "Подсказки:\n"
    "• Скажи *голос* или *voice*, чтобы включить голосовой режим; *текст* или *text* — чтобы вернуться к тексту.\n"
    "• Команда «озвучь …»/“speak …” — озвучит текст в любом режиме.\n"
    "• В переводчике сообщения переводятся *без лишних комментариев*: можно сразу копировать текст или слушать голосом."
)

HELP_TEXT_EN = (
    "🤖 *Help*\n\n"
    "Core commands:\n"
    "• /start — start or restart onboarding\n"
    "• /settings — language, level, style, output mode\n"
    "• /translator_on — enable translator mode\n"
    "• /translator_off — exit translator mode\n"
    "• /privacy — privacy policy\n"
    "• /delete_me — remove my data\n\n"
    "Payments & promo:\n"
    "• /buy — purchase a plan or pack\n"
    "• /promo — apply a promo code\n"
    "• /donate — support the project\n"
    "• /stars — purchase via Telegram Stars\n\n"
    "Quick tweaks (same as /settings):\n"
    "• /language — change learning language\n"
    "• /level — change level (A0–C2)\n"
    "• /style — switch style (Casual/Business)\n\n"
    "Tips:\n"
    "• Say *voice* (or in your UI language) to switch to voice mode; say *text* to switch back.\n"
    "• “speak …”/«озвучь …» — speak the text in any mode.\n"
    "• In translator mode, replies are *clean translations* with no extra chatter—copy or listen right away."
)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ui = get_ui_lang(update, context)
    text = HELP_TEXT_RU if ui == "ru" else HELP_TEXT_EN
    # parse_mode Markdown для жирного и курсива, но без HTML-тегов
    await update.effective_message.reply_text(text, parse_mode="Markdown")
