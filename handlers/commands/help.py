# handlers/commands/help.py
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from components.i18n import get_ui_lang

HELP_RU = (
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
    "• /teach — сказать Мэтту, как правильно\n"
    "• /glossary — посмотреть собственный глоссарий\n"
    "• /consent — почитать текст согласия на обучение\n"
    "\n"
    "Как эффективно общаться с Мэттом:\n"
    "• Мэтт — собеседник. Он не видит ваши настройки и оплату. Фразы вроде «поменяй уровень/язык/стиль» не сработают — "
    "для этого есть команды: /settings, /language, /level, /style; оплата — /buy, /donate и /promo для промокода.\n"
    "• Общайся голосом или текстом. Если интересно, как что-то звучит — скажи «озвучь» — "
    "Мэтт пришлёт аудио (разовая озвучка, режим не меняется).\n"
    "• Если у Мэтта что-то звучит неестественно или с произношением промах — используй /teach. "
    "После согласия — /consent_on — можно поправить его. Все корректировки сохранятся в /glossary.\n"
    "• Подсказка: в /settings изменения применяются сразу после выбора — можно просто продолжать диалог.\n"
    "• Помни: в бесплатном режиме доступно 15 сообщений в день; /start не обнуляет этот лимит.\n"
    "\n"
    "Обратная связь:\n"
    "Ты всегда можешь связаться с разработчиком и оставить отзыв о работе Мэтта: @marrona\n"
)

HELP_EN = (
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
    "• /teach — tell Matt the correct phrasing\n"
    "• /glossary — view your personal glossary\n"
    "• /consent — read the teaching consent\n"
    "\n"
    "How to get the most out of Matt:\n"
    "• Matt is a conversation partner. He doesn’t see your settings or billing. Saying “change my level/language/style” won’t work — "
    "use /settings, /language, /level, /style. Payments/promos go through /buy, /donate, and /promo.\n"
    "• You can chat in voice or text. If you want to hear how something sounds, say “voice it” — "
    "Matt will send a one-off audio reply (it doesn’t switch the mode).\n"
    "• If Matt’s pronunciation or phrasing feels off, use /teach. After you agree — /consent_on — you can correct him. "
    "All your corrections are saved in /glossary.\n"
    "• Tip: in /settings, changes apply immediately after you pick them — you can just keep chatting.\n"
    "• Remember: on the free plan you have 15 messages per day; /start does not reset this limit.\n"
    "\n"
    "Feedback:\n"
    "You can always contact the developer and leave feedback about Matt: @marrona\n"
)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ui = get_ui_lang(update, context)
    text = HELP_RU if ui == "ru" else HELP_EN
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)
