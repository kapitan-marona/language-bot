import os
import base64
import tempfile
import asyncio

from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
)

from config.config import TELEGRAM_TOKEN, WEBHOOK_SECRET_PATH
from components.profile_db import init_db
from components.onboarding import send_onboarding
from handlers.conversation_callback import handle_callback_query
from handlers.commands.admin import admin_command
from handlers.commands.user import users_command, user_command
from handlers.commands.reset import reset_command
from handlers.commands.test import test_command
from handlers.commands.broadcast import broadcast_command
from handlers.commands.promo import promo_command
from handlers.commands.stats import stats_command
from handlers.commands.debug import session_command
from handlers.commands.help import help_command


# ✅ Инициализация базы данных профилей (один раз при запуске)
init_db()

# ✅ Расшифровка GOOGLE_APPLICATION_CREDENTIALS_BASE64 на старте
encoded = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_BASE64")
if encoded:
    decoded = base64.b64decode(encoded)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        f.write(decoded)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name

# FastAPI-приложение
app = FastAPI()

# Telegram-приложение (бот)
bot_app: Application = None  # будет инициализирован при запуске

@app.on_event("startup")
async def on_startup():
    global bot_app
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Импортировать обработчики только тут (во избежание циклических импортов)
    from handlers.chat.chat_handler import handle_message
    # Регистрируем основные обработчики
    bot_app.add_handler(MessageHandler((filters.TEXT | filters.VOICE) & ~filters.COMMAND, handle_message))
    bot_app.add_handler(CommandHandler("start", send_onboarding))
    bot_app.add_handler(CallbackQueryHandler(handle_callback_query))
    # --- Регистрируем команды для админа
    bot_app.add_handler(CommandHandler("admin", admin_command))
    bot_app.add_handler(CommandHandler("users", users_command))
    bot_app.add_handler(CommandHandler("user", user_command))
    bot_app.add_handler(CommandHandler("reset", reset_command))
    bot_app.add_handler(CommandHandler("test", test_command))
    bot_app.add_handler(CommandHandler("broadcast", broadcast_command))
    bot_app.add_handler(CommandHandler("promo", promo_command))
    bot_app.add_handler(CommandHandler("stats", stats_command))
    bot_app.add_handler(CommandHandler("session", session_command))
    bot_app.add_handler(CommandHandler("help", help_command))
    # Инициализация Telegram Application (Webhook-режим)
    asyncio.create_task(bot_app.initialize())


@app.post(f"/{WEBHOOK_SECRET_PATH}")
async def telegram_webhook(req: Request):
    body = await req.json()
    update = Update.de_json(body, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}
