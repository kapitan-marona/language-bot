# english_bot.py
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, ApplicationBuilder, ContextTypes, MessageHandler, filters
from config.config import TELEGRAM_TOKEN, WEBHOOK_SECRET_PATH

import asyncio

app = FastAPI()
bot_app: Application = None  # глобально инициализируем позже


@app.on_event("startup")
async def on_startup():
    global bot_app
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Добавим обработчик входящих текстов
    from handlers.chat.chat_handler import handle_message
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # (опционально) обработчик голосовых сообщений — добавим позже

    # Запускаем polling loop в фоне (не нужен, если только webhook)
    asyncio.create_task(bot_app.initialize())


@app.post(f"/{WEBHOOK_SECRET_PATH}")
async def telegram_webhook(req: Request):
    body = await req.json()
    update = Update.de_json(body, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}
