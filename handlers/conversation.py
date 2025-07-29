from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from state.session import user_sessions

def get_interface_language_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="lang_en"),
            InlineKeyboardButton("Русский", callback_data="lang_ru"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Очищаем всю сессию, включая историю
    user_sessions[chat_id] = {}

    # Определяем язык интерфейса по умолчанию (пока принудительно ru)
    interface_lang = context.user_data.get("interface_lang", "ru")

    if interface_lang == "en":
        greeting = (
            "👋 Hi! I'm Matt — your personal language learning buddy!\n\n"
            "🌐 Let's start by choosing your interface language.\n"
            "No worries — even if it's your first time, I'll guide you!\n\n"
            "👇 Choose the language we'll be chatting in:"
        )
    else:
        greeting = (
            "👋 Привет! Я Мэтт — твой помощник для изучения языков!\n\n"
            "🌐 Давай начнем с выбора языка интерфейса.\n"
            "Не переживай — даже если это твой первый раз, я подскажу путь!\n\n"
            "👇 Выбери язык, на котором будем общаться:"
        )

    await update.message.reply_text(
        greeting,
        reply_markup=get_interface_language_keyboard()
    )
