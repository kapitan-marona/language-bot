from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

# 🎤 Voice mode buttons
voice_mode_button = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🔊 Voice mode")],
        [KeyboardButton("📋 Menu")],
        [KeyboardButton("🌐 Change language")]
    ],
    resize_keyboard=True
)

# ⌨️ Text mode buttons
text_mode_button = ReplyKeyboardMarkup(
    [
        [KeyboardButton("⌨️ Text mode")],
        [KeyboardButton("📋 Menu")],
        [KeyboardButton("🌐 Change language")]
    ],
    resize_keyboard=True
)

# 🌍 Language selection keyboard
learn_lang_keyboard = [
    ["English", "French", "Spanish", "German", "Italian"],
    ["Finnish", "Norwegian", "Swedish", "Russian", "Portuguese"]
]
learn_lang_markup = ReplyKeyboardMarkup(
    learn_lang_keyboard,
    one_time_keyboard=True,
    resize_keyboard=True
)

# 📈 Level selection
level_keyboard = [["Beginner", "Intermediate"]]
level_markup = ReplyKeyboardMarkup(
    level_keyboard,
    one_time_keyboard=True,
    resize_keyboard=True
)

# 🎭 Style selection (for Russian interface)
style_keyboard_ru = [["😎 Casual", "💼 Business"]]

# 📋 Main menu
main_menu_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("📖 Dictionary", callback_data="dictionary")]
])
