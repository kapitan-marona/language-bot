from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from components.profile_db import save_user_gender, get_user_gender
from state.session import user_sessions

GENDER_QUESTION = (
    "Спрошу форму обращения к тебе сразу, чтобы избежать неловких ситуаций 😅\n"
    "I’ll ask how to address you right away to avoid any awkward moments 😅"
)

def get_gender_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("муж", callback_data="gender_male"),
            InlineKeyboardButton("жен", callback_data="gender_female"),
            InlineKeyboardButton("друг", callback_data="gender_friend"),
        ],
        [
            InlineKeyboardButton("male", callback_data="gender_male"),
            InlineKeyboardButton("female", callback_data="gender_female"),
            InlineKeyboardButton("friend", callback_data="gender_friend"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_interface_language_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="lang_en"),
            InlineKeyboardButton("Русский", callback_data="lang_ru"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

PREPARING_MESSAGE = "⌨️ Подготовка…\n⌨️ Preparing…"

ONBOARDING_MESSAGE = (
    "👋 На связи Мэтт. / Matt here.\n\n"
    "🌐 Начнем с выбора языка интерфейса. Если потребуется, буду переводить непонятные слова на него. "
    "Жми на кнопку ниже, чтобы выбрать язык. ⬇️\n\n"
    "🌐 Let’s start by choosing your interface language. If needed, I’ll translate tricky words into it for you. "
    "Tap the button below to select a language. ⬇️"
)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Очищаем всю сессию, включая историю
    user_sessions[chat_id] = {}

    # Определяем язык интерфейса по умолчанию (теперь по-умолчанию "ru", но можно сменить)
    interface_lang = context.user_data.get("interface_lang", "ru")

    # Удаляем старые reply-кнопки
    await update.message.reply_text(PREPARING_MESSAGE, reply_markup=ReplyKeyboardRemove())

    # Новое приветствие без лишней строки — только кнопки!
    await update.message.reply_text(ONBOARDING_MESSAGE, reply_markup=get_interface_language_keyboard())

