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
    PreCheckoutQueryHandler,  # NEW: для Telegram Stars pre_checkout
    filters,
)

# === наши компоненты/хендлеры ===
from handlers.commands.help import help_command
from handlers.commands.payments import buy_command  # NEW
from components.payments import precheckout_ok, on_successful_payment  # NEW
from handlers.middleware.usage_gate import usage_gate  # NEW
from handlers.commands.teach import (  # NEW
    build_teach_handler,
    consent_on,
    consent_off,
    glossary_cmd,
)
from handlers.callbacks.menu import menu_router  # NEW
from handlers.callbacks import how_to_pay_game  # NEW

from components.profile_db import init_db as init_profiles_db  # NEW
from components.usage_db import init_usage_db  # NEW
from components.training_db import init_training_db  # NEW

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
TELEGRAM_WEBHOOK_SECRET_TOKEN = os.getenv("TELEGRAM_WEBHOOK_SECRET_TOKEN")  # NEW: секрет для подписи апдейтов

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
        allowed_updates=["message", "edited_message", "callback_query", "pre_checkout_query"],  # NEW
        secret_token=TELEGRAM_WEBHOOK_SECRET_TOKEN or None,  # NEW: Telegram будет слать этот же токен в заголовке
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
    app_.add_handler(CommandHandler("buy", buy_command))  # NEW

    # «Режим обучения» (глоссарий)
    app_.add_handler(CommandHandler("consent_on", consent_on))   # NEW
    app_.add_handler(CommandHandler("consent_off", consent_off)) # NEW
    app_.add_handler(CommandHandler("glossary", glossary_cmd))   # NEW
    app_.add_handler(build_teach_handler())                      # NEW

    # Платежи Stars
    app_.add_handler(PreCheckoutQueryHandler(precheckout_ok))                    # NEW
    app_.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_successful_payment))  # NEW

    # Кнопки меню
    app_.add_handler(CallbackQueryHandler(menu_router, pattern=r"^open:", block=True))  # NEW

    # Интерактивная инструкция «Как оплатить?»
    app_.add_handler(CallbackQueryHandler(how_to_pay_game.how_to_pay_entry, pattern=r"^htp_start$", block=True))  # NEW
    app_.add_handler(CallbackQueryHandler(how_to_pay_game.how_to_pay_how, pattern=r"^htp_how$", block=True))      # NEW
    app_.add_handler(CallbackQueryHandler(how_to_pay_game.how_to_pay_exit, pattern=r"^htp_exit$", block=True))    # NEW
    app_.add_handler(CallbackQueryHandler(how_to_pay_game.how_to_pay_go_buy, pattern=r"^htp_buy$", block=True))   # NEW

    # Гейт лимитов (15/сутки) — ставим «выше» основного обработчика диалога
    app_.add_handler(MessageHandler(filters.TEXT | filters.VOICE | filters.AUDIO, usage_gate), group=0)  # NEW


# -----------------------------------------------------------------------------
# Инициализация БД и запуск
# -----------------------------------------------------------------------------
def init_databases():
    init_profiles_db()  # NEW
    init_usage_db()     # NEW
    init_training_db()  # NEW


@app.on_event("startup")
async def on_startup():
    init_databases()         # NEW
    setup_handlers(bot_app)  # NEW
    logger.info("Bot application is ready")


# -----------------------------------------------------------------------------
# Локальный запуск Uvicorn:
# uvicorn english_bot:app --host 0.0.0.0 --port 8000
# -----------------------------------------------------------------------------
