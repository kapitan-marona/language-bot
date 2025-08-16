from telegram.ext import Application
from .conversation import (
    start,
    learn_lang_choice,
    level_choice,
    style_choice,
    cancel,
)
from telegram.ext import CommandHandler, MessageHandler, ConversationHandler, filters
from handlers.toggle_mode import toggle_mode
from voice import handle_voice_message
from .chat.chat_handler import chat

def register_handlers(application: Application) -> None:
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            0: [MessageHandler(filters.TEXT & ~filters.COMMAND, learn_lang_choice)],
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, level_choice)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, style_choice)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(MessageHandler(filters.Regex(r"^🔊 Voice mode$|^⌨️ Text mode$"), toggle_mode))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

