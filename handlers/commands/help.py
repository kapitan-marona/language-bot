from telegram import Update
from telegram.ext import ContextTypes

async def help_command(update, context):
    await update.message.reply_text(
        "Доступные команды:\n"
        "/admin — админ-панель\n"
        "/users — список пользователей\n"
        "/user — режим пользователя\n"
        "/reset — сброс профиля\n"
        "/test — тестовая команда\n"
        "/broadcast — рассылка\n"
        "/promo — промокоды\n"
        "/stats — статистика\n"
        "/session — информация о сессии\n"
        "/help — справка"
    )
