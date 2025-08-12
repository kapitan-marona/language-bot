# english_bot.py
from __future__ import annotations

import os
import logging
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,  # для Telegram Stars pre_checkout
    filters,
)

# === наши компоненты/хендлеры ===
from handlers.conversation_callback import conversation_callback
from handlers.commands.help import help_command
from handlers.commands.payments import buy_command
from components.payments import precheckout_ok, on_successful_payment
from handlers.middleware.usage_gate import usage_gate
from handlers.commands.teach import (
    build_teach_handler,
    consent_on,
    consent_off,
    glossary_cmd,
)
from handlers.callbacks.menu import menu_router
from handlers.callbacks import how_to_pay_game

from components.profile_db import init_db as init_profiles_db
from components.usage_db import init_usage_db
from components.training_db import init_training_db

# -----------------------------------------------------------------------------
# Инициализация
# -----------------------------------------------------------------------------
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")

WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH")
if not WEBHOOK_SECRET_PATH:
    raise RuntimeError("WEBHOOK_SECRET_PATH is not set")

PUBLIC_URL = os.getenv("PUBLIC_URL")  # например, https://english-talking-bot.onrender.com
TELEGRAM_WEBHOOK_SECRET_TOKEN = os.getenv("TELEGRAM_WEBHOOK_SECRET_TOKEN")  # секрет для подписи апдейтов

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("english-bot")

app = FastAPI(title="English Talking Bot")

# Создаём приложение python-telegram-bot
bot_app: Application = Application.builder().token(TELEGRAM_TOKEN).build()


# -----------------------------------------------------------------------------
# Обработчики ошибок
# -----------------------------------------------------------------------------
async def on_error(update: Optional[Update], context):
    logger.exception("Unhandled error: %s", context.error)


# -----------------------------------------------------------------------------
# Роуты FastAPI
# -----------------------------------------------------------------------------
@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.post(f"/{WEBHOOK_SECRET_PATH}")
async def telegram_webhook(req: Request):
    # проверка секрета (если задан)
    if TELEGRAM_WEBHOOK_SECRET_TOKEN:
        got = req.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if got != TELEGRAM_WEBHOOK_SECRET_TOKEN:
            logger.warning("Forbidden: bad webhook secret token")
            return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)

    # читаем JSON безопасно
    try:
        data = await req.json()
    except Exception as e:
        logger.warning("Bad JSON in webhook: %s", e)
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)

    # парсим Update и отдаём в PTB
    try:
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
    except Exception as e:
        # важно: не отдаём 500, чтобы Telegram не заспамил ретраями
        logger.exception("Webhook handling error: %s", e)
        return JSONResponse({"ok": False, "error": "internal"}, status_code=200)

    return {"ok": True}


# Утилита для ручной установки вебхука (например, через браузер/студио)
@app.get("/set_webhook")
async def set_webhook(url: Optional[str] = Query(default=None)):
    """
    Устанавливает вебхук. Если параметр url не передан, собирает из PUBLIC_URL.
    """
    target = url or (f"{PUBLIC_URL.rstrip('/')}/{WEBHOOK_SECRET_PATH}" if PUBLIC_URL else None)
    if not target:
        return JSONResponse({"ok": False, "error": "PUBLIC_URL is not set"}, status_code=400)

    logger.info("Setting webhook to %s", target)
    ok = await bot_app.bot.set_webhook(
        url=target,
        drop_pending_updates=True,
        allowed_updates=["message", "edited_message", "callback_query", "pre_checkout_query"],
        secret_token=TELEGRAM_WEBHOOK_SECRET_TOKEN or None,  # Telegram будет слать этот же токен в заголовке
    )
    return {"ok": ok, "url": target}


# -----------------------------------------------------------------------------
# Регистрация хендлеров Telegram
# -----------------------------------------------------------------------------
def setup_handlers(app_: Application):
    # Ошибки
    app_.add_error_handler(on_error)

    # Команды
    app_.add_handler(CommandHandler("help", help_command))
    app_.add_handler(CommandHandler("buy", buy_command))

    # «Режим обучения» (глоссарий)
    app_.add_handler(CommandHandler("consent_on", consent_on))
    app_.add_handler(CommandHandler("consent_off", consent_off))
    app_.add_handler(CommandHandler("glossary", glossary_cmd))
    app_.add_handler(build_teach_handler())

    # Платежи Stars
    app_.add_handler(PreCheckoutQueryHandler(precheckout_ok))
    app_.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_successful_payment))

    # Кнопки меню
    app_.add_handler(CallbackQueryHandler(menu_router, pattern=r"^open:", block=True))

    # Интерактивная инструкция «Как оплатить?»
    app_.add_handler(CallbackQueryHandler(how_to_pay_game.how_to_pay_entry, pattern=r"^htp_start$", block=True))
    app_.add_handler(CallbackQueryHandler(how_to_pay_game.how_to_pay_how, pattern=r"^htp_how$", block=True))
    app_.add_handler(CallbackQueryHandler(how_to_pay_game.how_to_pay_exit, pattern=r"^htp_exit$", block=True))
    app_.add_handler(CallbackQueryHandler(how_to_pay_game.how_to_pay_go_buy, pattern=r"^htp_buy$", block=True))

    # Гейт лимитов (15/сутки) — ставим «выше» основного обработчика диалога
    app_.add_handler(MessageHandler(filters.TEXT | filters.VOICE | filters.AUDIO, usage_gate), group=0)
    app_.add_handler(MessageHandler(filters.TEXT | filters.VOICE | filters.AUDIO, conversation_callback), group=1)


# -----------------------------------------------------------------------------
# Инициализация БД и запуск/останов PTB
# -----------------------------------------------------------------------------
def init_databases():
    init_profiles_db()
    init_usage_db()
    init_training_db()


@app.on_event("startup")
async def on_startup():
    init_databases()
    setup_handlers(bot_app)
    # КЛЮЧЕВОЕ: инициализируем и запускаем PTB-приложение для вебхука
    await bot_app.initialize()
    await bot_app.start()
    logger.info("Bot application is ready")


@app.on_event("shutdown")
async def on_shutdown():
    # КЛЮЧЕВОЕ: корректно останавливаем PTB-приложение
    await bot_app.stop()
    await bot_app.shutdown()
    logger.info("Bot application is stopped")


# -----------------------------------------------------------------------------
# Локальный запуск Uvicorn:
# uvicorn english_bot:app --host 0.0.0.0 --port 8000
# -----------------------------------------------------------------------------
