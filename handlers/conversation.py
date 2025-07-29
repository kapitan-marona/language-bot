from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from state.session import user_sessions


def get_interface_language_keyboard() -> InlineKeyboardMarkup:
    """Кнопки выбора языка интерфейса"""
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="lang_en"),
            InlineKeyboardButton("Русский", callback_data="lang_ru"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Очищаем предыдущую сессию
    user_sessions[chat_id] = {}

    text = (
        "🌐 Let's start by choosing the language for our interface.\n\n"
        "⚠️ Don't worry — even if it's your first time using this language, I'm here to help! "
        "We'll take it slow, and I'll guide you step by step.\n\n"
        "👇 Choose your interface language:"
    )

    await update.message.reply_text(text, reply_markup=get_interface_language_keyboard())

