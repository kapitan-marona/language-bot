from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from .keyboards import main_menu_keyboard

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📋 Главное меню:", reply_markup=main_menu_keyboard)

async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    query = update.callback_query
    await query.answer()

    if query.data == "dictionary":
        words = context.user_data.get("dictionary", set())
        if not words:
            await query.edit_message_text("📖 Пока что словарь пуст.")
        else:
            sorted_words = sorted(words)
            word_list = "\n".join(f"• {w}" for w in sorted_words)
            await query.edit_message_text(f"📚 Вот твои недавние слова:\n\n{word_list}")
        return ConversationHandler.END

    await query.edit_message_text("Меню пока пустое. Скоро тут появятся новые возможности! 🛠️")
    return ConversationHandler.END
