import time
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application
from config import TELEGRAM_TOKEN, WEBHOOK_SECRET_PATH
from handlers.registry import register_handlers

# FastAPI app instance
app = FastAPI()

# Telegram bot application
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Register all handlers in a separate module
register_handlers(application)

# In-memory rate limiter
user_last_called = {}
RATE_LIMIT_SECONDS = 3

@app.post(f"/webhook/{WEBHOOK_SECRET_PATH}")
async def webhook_handler(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    user_id = update.effective_user.id if update.effective_user else None

    if user_id:
        now = time.time()
        last_call = user_last_called.get(user_id, 0)
        if now - last_call < RATE_LIMIT_SECONDS:
            return {"status": "rate_limited"}
        user_last_called[user_id] = now

    await application.initialize()
    await application.process_update(update)
    return {"status": "ok"}
