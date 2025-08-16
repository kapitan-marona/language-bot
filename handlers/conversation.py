from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, ContextTypes
from .keyboards import learn_lang_markup, level_markup, style_keyboard_ru
from .chat.prompts import generate_system_prompt, rebuild_system_prompt
from .chat.messages import start_messages, level_messages, style_messages, welcome_messages

STYLE_MAP = {
    "😎 casual": "casual", "casual": "casual", "разговорный": "casual",
    "💼 business": "formal", "business": "formal", "деловой": "formal", "formal": "formal"
}
LEVEL_MAP = {"beginner": "A1-A2", "intermediate": "B1-B2"}
def norm(s: str) -> str: return s.strip().lower()

import random

LEARN_LANG, LEVEL, STYLE = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    user_locale = update.effective_user.language_code or "en"
    lang = "Русский" if user_locale.startswith("ru") else "English"
    context.user_data["language"] = lang

    await update.message.reply_text(
        random.choice(start_messages[lang]),
        reply_markup=learn_lang_markup
    )
    return LEARN_LANG

async def learn_lang_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["learn_lang"] = update.message.text
    lang = context.user_data["language"]
    await update.message.reply_text(
        random.choice(level_messages[lang]),
        reply_markup=level_markup
    )
    return LEVEL

async def level_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = norm(update.message.text)
    context.user_data["level"] = LEVEL_MAP.get(raw, update.message.text)
    lang = context.user_data["language"]
    await update.message.reply_text(
        random.choice(style_messages[lang]),
        reply_markup=ReplyKeyboardMarkup(style_keyboard_ru, one_time_keyboard=True, resize_keyboard=True)
    )
    return STYLE

async def style_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = norm(update.message.text)
    context.user_data["style"] = STYLE_MAP.get(raw, "casual")
    context.user_data.setdefault("voice_mode", False)
    rebuild_system_prompt(context)
    
    context.user_data["mode_button_shown"] = False

    lang = context.user_data.get("language", "English")
    welcome = random.choice(welcome_messages.get(lang, welcome_messages["English"]))
    await update.message.reply_text(welcome, reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Диалог отменён.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
