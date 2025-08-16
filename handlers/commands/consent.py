# handlers/commands/consent.py
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from components.i18n import get_ui_lang

TEXT_RU = (
    "📄 Согласие на обучение\n\n"
    "Что это:\n"
    "• Режим /teach позволяет тебе подсказывать Мэтту более точные формулировки и произношение.\n"
    "• Твои правки сохраняются в /glossary и используются, чтобы Мэтт говорил естественнее именно для тебя.\n\n"
    "Как включить/выключить:\n"
    "• Включить согласие — /consent_on\n"
    "• Отключить согласие — /consent_off\n\n"
    "Приватность:\n"
    "• Правки применяются только в твоих диалогах и не влияют на других пользователей.\n"
    "• Ты можешь отключить согласие в любой момент командой /consent_off.\n\n"
    "Подсказка:\n"
    "• После включения согласия просто используй /teach, чтобы поправить Мэтта, когда что-то звучит неестественно."
)

TEXT_EN = (
    "📄 Consent for Teaching Mode\n\n"
    "What it is:\n"
    "• The /teach mode lets you give Matt more natural phrasing and pronunciation.\n"
    "• Your corrections are saved in /glossary and help Matt sound better specifically for you.\n\n"
    "How to enable/disable:\n"
    "• Enable consent — /consent_on\n"
    "• Disable consent — /consent_off\n\n"
    "Privacy:\n"
    "• Corrections apply only to your chats and do not affect other users.\n"
    "• You can disable consent anytime with /consent_off.\n\n"
    "Tip:\n"
    "• After enabling consent, just use /teach whenever something sounds off."
)

async def consent_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ui = get_ui_lang(update, context)
    text = TEXT_RU if ui == "ru" else TEXT_EN
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)
