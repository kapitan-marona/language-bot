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

# Универсальное "Подготовка..." (можно расширить на другие языки)
PREPARING_MESSAGES = {
    "ru": "⌨️ Подготовка…",
    "en": "⌨️ Preparing…"
}

# Новое приветствие без лишней строки перед кнопками
ONBOARDING_MESSAGES = {
    "ru": (
        "👋 На связи Мэтт.\n\n"
        "🌐 Начнем с выбора языка интерфейса. Если потребуется, буду переводить непонятные слова на него. "
        "Жми на кнопку ниже, чтобы выбрать язык. ⬇️"
    ),
    "en": (
        "👋 Matt here.\n\n"
        "🌐 Let’s start by choosing your interface language. If needed, I’ll translate tricky words into it for you. "
        "Tap the button below to select a language. ⬇️"
    ),
}

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Очищаем всю сессию, включая историю
    user_sessions[chat_id] = {}

    # Определяем язык интерфейса по умолчанию (теперь по-умолчанию "ru", но можно сменить)
    interface_lang = context.user_data.get("interface_lang", "ru")

    # Удаляем старые reply-кнопки
    await update.message.reply_text(
        PREPARING_MESSAGES.get(interface_lang, PREPARING_MESSAGES["en"]),
        reply_markup=ReplyKeyboardRemove()
    )

    # Новое приветствие без лишней строки — только кнопки!
    await update.message.reply_text(
        ONBOARDING_MESSAGES.get(interface_lang, ONBOARDING_MESSAGES["en"]),
        reply_markup=get_interface_language_keyboard()
    )
