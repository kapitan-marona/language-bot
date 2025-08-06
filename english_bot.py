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
from handlers.conversation import handle_start, handle_callback_query


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
    from handlers.chat.chat_handler import handle_message, admin_command, users_command
    from handlers.conversation import handle_start, handle_callback_query

    # Регистрируем основные обработчики
    bot_app.add_handler(MessageHandler((filters.TEXT | filters.VOICE) & ~filters.COMMAND, handle_message))
    bot_app.add_handler(CommandHandler("start", handle_start))
    bot_app.add_handler(CallbackQueryHandler(handle_callback_query))

    # --- Регистрируем команды для админа
    bot_app.add_handler(CommandHandler("admin", admin_command))
    bot_app.add_handler(CommandHandler("users", users_command))

    # Инициализация Telegram Application (Webhook-режим)
    asyncio.create_task(bot_app.initialize())


@app.post(f"/{WEBHOOK_SECRET_PATH}")
async def telegram_webhook(req: Request):
    body = await req.json()
    update = Update.de_json(body, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}
