import os
import base64
import tempfile
import asyncio
import logging

from config.logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

from handlers.error_handler import on_error

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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
try:
    init_db()
    logger.info("Profile DB initialized")
except Exception:
    logger.exception("Failed to initialize profile DB")

# ✅ Расшифровка GOOGLE_APPLICATION_CREDENTIALS_BASE64 на старте
_tmp_creds_path: str | None = None
encoded = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_BASE64")
if encoded:
    try:
        decoded = base64.b64decode(encoded)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            f.write(decoded)
            _tmp_creds_path = f.name
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _tmp_creds_path
        logger.info("Google credentials decoded to temp file")
    except Exception:
        logger.exception("Failed to decode GOOGLE_APPLICATION_CREDENTIALS_BASE64")

# FastAPI-приложение
app = FastAPI()

# Telegram-приложение (бот)
bot_app: Application | None = None  # будет инициализирован при запуске

@app.on_event("startup")
async def on_startup():
    global bot_app

    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is not set")
        return

    try:
        bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        bot_app.add_error_handler(on_error)

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

        asyncio.create_task(bot_app.initialize())
        logger.info("Telegram Application initialized")
    except Exception:
        logger.exception("Failed to initialize Telegram Application")

@app.on_event("shutdown")
async def on_shutdown():
    # Аккуратно чистим временный файл с кредами (если создавали)
    global _tmp_creds_path
    if _tmp_creds_path:
        try:
            os.remove(_tmp_creds_path)
            logger.info("Removed temp Google credentials file")
        except Exception:
            logger.warning("Failed to remove temp Google credentials file")
        _tmp_creds_path = None

@app.post(f"/{WEBHOOK_SECRET_PATH}")
async def telegram_webhook(req: Request):
    global bot_app
    if bot_app is None:
        logger.error("bot_app is None on webhook call")
        return JSONResponse({"ok": False, "error": "bot not ready"}, status_code=503)

    try:
        body = await req.json()
    except Exception:
        logger.exception("Invalid JSON in webhook request")
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)

    try:
        update = Update.de_json(body, bot_app.bot)
        await bot_app.process_update(update)
        return {"ok": True}
    except Exception:
        logger.exception("Error while processing update")
        return JSONResponse({"ok": False, "error": "processing error"}, status_code=500)
