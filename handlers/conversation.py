from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

    text = (
        "👋 Привет! Я Мэтт, и я помогу тебе выучить новый язык!\n\n"
        "🌐 Давай начнем с выбора языка интерфейса. "
        "Не переживай — даже если это твой первый раз, я подскажу путь!\n\n"
        "👇 Выбери язык, на котором будем общаться:"
    )

    await update.message.reply_text(text, reply_markup=get_interface_language_keyboard())
