# handlers/commands/consent.py
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from components.i18n import get_ui_lang
from components.lang_codes import LANG_CODES

TEXT_RU = (
    "📄 Согласие на обучение\n\n"
    "Что это:\n"
    "• /teach позволяет подсказывать Мэтту более естественные формулировки.\n"
    "• Твои правки сохраняются в /glossary и используются только в твоих диалогах.\n\n"
    "Как включить/выключить:\n"
    "• Включить — /consent_on\n"
    "• Отключить — /consent_off\n\n"
    "Как использовать /teach:\n"
    "1) Отправь языковую пару (две буквы ISO-639-1), например: en-ru, en-fi, ru-en, ru-es. Полный список — /codes\n"
    "2) Затем пришли список строк «фраза — перевод», по одной на строку.\n"
    "   Пример:\n"
    "   I feel you — Понимаю тебя\n"
    "   Break a leg — Удачи!\n"
    "3) Готово — всё попадёт в /glossary. Спасибо! Ты делаешь Мэтта лучше ❤️\n\n"
    "Приватность:\n"
    "• Правки применяются только для тебя и не влияют на других пользователей.\n"
    "• Нецензурная лексика автоматически блокируется."
)

TEXT_EN = (
    "📄 Teaching Consent\n\n"
    "What it is:\n"
    "• /teach lets you provide more natural phrasing for Matt.\n"
    "• Your entries are saved in /glossary and used only in your chats.\n\n"
    "How to enable/disable:\n"
    "• Enable — /consent_on\n"
    "• Disable — /consent_off\n\n"
    "How to use /teach:\n"
    "1) Send a language pair (two-letter ISO-639-1 codes), e.g., en-ru, en-fi, ru-en, ru-es. Full list — /codes\n"
    "2) Then send a list of lines in the format “phrase — translation”, one per line.\n"
    "   Example:\n"
    "   I feel you — Понимаю тебя\n"
    "   Break a leg — Удачи!\n"
    "3) Done — everything goes to /glossary. Thanks! You’re making Matt better ❤️\n\n"
    "Privacy:\n"
    "• Corrections apply only to your chats and do not affect other users.\n"
    "• Profanity is automatically blocked."
)

async def consent_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ui = get_ui_lang(update, context)
    text = TEXT_RU if ui == "ru" else TEXT_EN
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

async def codes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ui = get_ui_lang(update, context)
    heads = "🧾 Коды языков (ISO-639-1):\n" if ui == "ru" else "🧾 Language codes (ISO-639-1):\n"
    lines = []
    for code, name in sorted(LANG_CODES.items()):
        lines.append(f"{code} — {name}")
    await context.bot.send_message(chat_id=update.effective_chat.id, text=heads + "\n".join(lines))
