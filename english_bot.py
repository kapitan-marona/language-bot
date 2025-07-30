import os
import base64
import tempfile

# ✅ Расшифровка GOOGLE_APPLICATION_CREDENTIALS_BASE64 на старте
encoded = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_BASE64")
if encoded:
    decoded = base64.b64decode(encoded)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        f.write(decoded)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name

import os
import base64
import tempfile

# ✅ Расшифровка GOOGLE_APPLICATION_CREDENTIALS_BASE64 на старте
encoded = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_BASE64")
if encoded:
    decoded = base64.b64decode(encoded)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        f.write(decoded)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name

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
from handlers.conversation import handle_start
from handlers.conversation_callback import handle_callback_query
from state.session import user_sessions

import asyncio

# FastAPI-приложение
app = FastAPI()

# Telegram-приложение (бот)
bot_app: Application = None  # будет инициализирован при запуске


@app.on_event("startup")
async def on_startup():
    global bot_app
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Импорт обработчика текстовых сообщений
    from handlers.chat.chat_handler import handle_message

    # Регистрируем обработчики
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    bot_app.add_handler(CommandHandler("start", handle_start))
    bot_app.add_handler(CallbackQueryHandler(handle_callback_query))

    # Инициализация приложения Telegram (нужно при использовании Webhook)
    asyncio.create_task(bot_app.initialize())


@app.post(f"/{WEBHOOK_SECRET_PATH}")
async def telegram_webhook(req: Request):
    body = await req.json()
    update = Update.de_json(body, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}




