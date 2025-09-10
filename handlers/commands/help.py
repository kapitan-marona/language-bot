from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes

from components.i18n import get_ui_lang

HELP_TEXT_RU = (
    "<b>🤖 Помощь</b>\n\n"
    "<b>Основные команды:</b>\n"
    "• <code>/start</code> — начать или перезапустить онбординг\n"
    "• <code>/settings</code> — язык, уровень, стиль, режим вывода\n"
    "• <code>/translator_on</code> — включить режим переводчика\n"
    "• <code>/translator_off</code> — выйти из режима переводчика\n"
    "• <code>/privacy</code> — политика конфиденциальности\n"
    "• <code>/delete_me</code> — удалить мои данные\n\n"
    "<b>Оплата и промо:</b>\n"
    "• <code>/buy</code> — оформить подписку или пакет\n"
    "• <code>/promo</code> — активировать промокод\n"
    "• <code>/donate</code> — поддержать проект\n"
    "• <code>/stars</code> — оформить через Telegram Stars\n\n"
    "<b>Быстрые настройки (дублируют /settings):</b>\n"
    "• <code>/language</code> — сменить язык изучения\n"
    "• <code>/level</code> — сменить уровень (A0–C2)\n"
    "• <code>/style</code> — переключить стиль (Разговорный/Деловой)\n\n"
    "<b>Подсказки:</b>\n"
    "• Скажи <i>голос</i> или <i>voice</i>, чтобы включить голосовой режим; <i>текст</i> или <i>text</i> — чтобы вернуться к тексту.\n"
    "• Команда «озвучь …» / “speak …” — озвучит текст в любом режиме.\n"
    "• В переводчике ответы — это <i>чистый перевод без лишних комментариев</i>: можно сразу копировать или слушать."
)

HELP_TEXT_EN = (
    "<b>🤖 Help</b>\n\n"
    "<b>Core commands:</b>\n"
    "• <code>/start</code> — start or restart onboarding\n"
    "• <code>/settings</code> — language, level, style, output mode\n"
    "• <code>/translator_on</code> — enable translator mode\n"
    "• <code>/translator_off</code> — exit translator mode\n"
    "• <code>/privacy</code> — privacy policy\n"
    "• <code>/delete_me</code> — remove my data\n\n"
    "<b>Payments & promo:</b>\n"
    "• <code>/buy</code> — purchase a plan or pack\n"
    "• <code>/promo</code> — apply a promo code\n"
    "• <code>/donate</code> — support the project\n"
    "• <code>/stars</code> — purchase via Telegram Stars\n\n"
    "<b>Quick tweaks (same as /settings):</b>\n"
    "• <code>/language</code> — change learning language\n"
    "• <code>/level</code> — change level (A0–C2)\n"
    "• <code>/style</code> — switch style (Casual/Business)\n\n"
    "<b>Tips:</b>\n"
    "• Say <i>voice</i> (or in your UI language) to switch to voice mode; say <i>text</i> to switch back.\n"
    "• “speak …” / «озвучь …» — speak the text in any mode.\n"
    "• In translator mode, replies are <i>clean translations with no extra chatter</i>—copy or listen right away."
)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ui = get_ui_lang(update, context)
    text = HELP_TEXT_RU if ui == "ru" else HELP_TEXT_EN
    await update.effective_message.reply_text(text, parse_mode="HTML")
