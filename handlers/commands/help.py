# handlers/commands/help.py
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import ContextTypes

def _ui_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return (context.user_data or {}).get("ui_lang", "ru")

def _help_text_ru() -> str:
    return (
        "Привет! Я Мэтт — твой друг для английского.\n\n"
        "⚙️ <b>Настройки</b> — /settings\n"
        "• Меняй язык, уровень и стиль общения.\n\n"
        "🎛 <b>Режим</b> — /mode\n"
        "• Выбирай, как будем общаться.\n\n"
        "🎟️ <b>Промокод</b> — /promo\n"
        "• Узнай срок действия кода.\n\n"
        "💬 <b>Обратная связь</b>\n"
        "• Напиши разработчику."
    )

def _help_text_en() -> str:
    return (
        "Hey! I’m Matt — your friend for English.\n\n"
        "⚙️ <b>Settings</b> — /settings\n"
        "• Change language, level, and chat style.\n\n"
        "🎛 <b>Mode</b> — /mode\n"
        "• Choose how we chat.\n\n"
        "🎟️ <b>Promo code</b> — /promo\n"
        "• Check your code expiry.\n\n"
        "💬 <b>Feedback</b>\n"
        "• Message the developer."
    )

def _reply_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton("⚙️ /settings"), KeyboardButton("🎛 /mode")],
        [KeyboardButton("🎟️ /promo")],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)

def _inline_keyboard(lang: str) -> InlineKeyboardMarkup:
    label = "💬 Написать разработчику" if lang == "ru" else "💬 Message the developer"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, url="https://t.me/marrona")]])

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _ui_lang(context)
    text = _help_text_ru() if lang == "ru" else _help_text_en()

    await update.message.reply_html(text, reply_markup=_reply_keyboard())
    await update.message.reply_text(
        "Если нужен быстрый контакт — нажми кнопку ниже:" if lang == "ru"
        else "Need a quick contact? Tap the button below:",
        reply_markup=_inline_keyboard(lang),
    )
