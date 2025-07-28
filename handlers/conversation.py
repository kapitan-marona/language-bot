# handlers/conversation.py

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

keyboard = [
    ["🇬🇧 English", "🇫🇷 French"],
    ["🇪🇸 Spanish", "🇩🇪 German"]
]

markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я помогу тебе практиковать иностранный язык.\nВыбери язык, который хочешь учить:",
        reply_markup=markup
    )
