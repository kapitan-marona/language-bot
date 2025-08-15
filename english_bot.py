from __future__ import annotations
import os
import logging
import asyncio  # неблокирующая обработка апдейтов
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
    PreCheckoutQueryHandler,
    filters,
)

# === наши компоненты/хендлеры ===
from handlers.chat.chat_handler import handle_message
from handlers.conversation_callback import handle_callback_query
from handlers.commands.help import help_command
from handlers.commands.payments import buy_command
from handlers.commands.promo import promo_command
from handlers.commands.donate import donate_command
from handlers import settings
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

# Онбординг и сброс
from handlers.commands.reset import reset_command
from components.onboarding import send_onboarding

from components.profile_db import init_db as init_profiles_db
from components.usage_db import init_usage_db
from components.training_db import init_training_db

from handlers.commands.language_cmd import language_command, language_on_callback
from handlers.commands.level_cmd import level_command, level_on_callback
from handlers.commands.style_cmd import style_command, style_on_callback
from handlers.commands import donate as donate_handlers

# -------------------------------------------------------------------------
# Инициализация
# -------------------------------------------------------------------------
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")

WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH")
if not WEBHOOK_SECRET_PATH:
    raise RuntimeError("WEBHOOK_SECRET_PATH is not set")

PUBLIC_URL = os.getenv("PUBLIC_URL")
TELEGRAM_WEBHOOK_SECRET_TOKEN = os.getenv("TELEGRAM_WEBHOOK_SECRET_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("english-bot")

app = FastAPI(title="English Talking Bot")
bot_app: Application = Application.builder().token(TELEGRAM_TOKEN).build()

# -------------------------------------------------------------------------
# Ошибки
# -------------------------------------------------------------------------
async def on_error(update: Optional[Update], context):
    logger.exception("Unhandled error: %s", context.error)

# -------------------------------------------------------------------------
# Роуты
# -------------------------------------------------------------------------
@app.get("/healthz")
async def healthz():
    return {"ok": True}

@app.post(f"/{WEBHOOK_SECRET_PATH}")
async def telegram_webhook(req: Request):
    if TELEGRAM_WEBHOOK_SECRET_TOKEN:
        got = req.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if got != TELEGRAM_WEBHOOK_SECRET_TOKEN:
            logger.warning("Forbidden: bad webhook secret token")
            return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)
    try:
        data = await req.json()
    except Exception as e:
        logger.warning("Bad JSON in webhook: %s", e)
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    try:
        update = Update.de_json(data, bot_app.bot)
        # было: await bot_app.process_update(update)
        asyncio.create_task(bot_app.process_update(update))  # неблокирующе
    except Exception as e:
        logger.exception("Webhook handling error: %s", e)
        # всё равно даём 200, чтобы Telegram не дропал вебхук
        return JSONResponse({"ok": False, "error": "internal"}, status_code=200)
    return {"ok": True}

@app.get("/set_webhook")
async def set_webhook(url: Optional[str] = Query(default=None)):
    target = url or (f"{PUBLIC_URL.rstrip('/')}/{WEBHOOK_SECRET_PATH}" if PUBLIC_URL else None)
    if not target:
        return JSONResponse({"ok": False, "error": "PUBLIC_URL is not set"}, status_code=400)
    logger.info("Setting webhook to %s", target)
    ok = await bot_app.bot.set_webhook(
        url=target,
        drop_pending_updates=True,
        allowed_updates=["message", "edited_message", "callback_query", "pre_checkout_query"],
        secret_token=TELEGRAM_WEBHOOK_SECRET_TOKEN or None,
    )
    return {"ok": ok, "url": target}

# -------------------------------------------------------------------------
# Хендлеры
# -------------------------------------------------------------------------
def setup_handlers(app_: "Application"):
    app_.add_error_handler(on_error)

    # Команды
    app_.add_handler(CommandHandler("start", lambda u, c: send_onboarding(u, c)))
    app_.add_handler(CommandHandler("reset", reset_command))
    app_.add_handler(CommandHandler("help", help_command))
    app_.add_handler(CommandHandler("buy", buy_command))
    app_.add_handler(CommandHandler("promo", promo_command))
    app_.add_handler(CommandHandler("donate", donate_command))
    app_.add_handler(CommandHandler("settings", settings.cmd_settings))

    # быстрые команды
    app_.add_handler(CommandHandler("language", language_command))
    app_.add_handler(CommandHandler("level", level_command))
    app_.add_handler(CommandHandler("style", style_command))

    # Teach/Glossary
    app_.add_handler(CommandHandler("consent_on", consent_on))
    app_.add_handler(CommandHandler("consent_off", consent_off))
    app_.add_handler(CommandHandler("glossary", glossary_cmd))
    app_.add_handler(build_teach_handler())

    # Платежи Stars
    app_.add_handler(PreCheckoutQueryHandler(precheckout_ok))
    app_.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_successful_payment))

    # Числовой ввод доната — ОБЯЗАТЕЛЬНО block=True, чтобы не шло в usage_gate/диалог
    app_.add_handler(
        MessageHandler(filters.Regex(r"^\s*\d{1,5}\s*$"), donate_handlers.on_amount_message, block=True),
        group=0,
    )

    # Callback’и меню, настроек, how-to-pay
    app_.add_handler(CallbackQueryHandler(menu_router, pattern=r"^open:", block=True))
    app_.add_handler(CallbackQueryHandler(settings.on_callback, pattern=r"^(SETTINGS:|SET:)", block=True))
    app_.add_handler(CallbackQueryHandler(how_to_pay_game.how_to_pay_entry, pattern=r"^htp_start$", block=True))
    app_.add_handler(CallbackQueryHandler(how_to_pay_game.how_to_pay_how, pattern=r"^htp_how$", block=True))
    app_.add_handler(CallbackQueryHandler(how_to_pay_game.how_to_pay_exit, pattern=r"^htp_exit$", block=True))
    app_.add_handler(CallbackQueryHandler(how_to_pay_game.how_to_pay_go_buy, pattern=r"^htp_buy$", block=True))
    app_.add_handler(CallbackQueryHandler(language_on_callback, pattern=r"^CMD:LANG:", block=True))
    app_.add_handler(CallbackQueryHandler(level_on_callback, pattern=r"^CMD:LEVEL:", block=True))
    app_.add_handler(CallbackQueryHandler(style_on_callback, pattern=r"^CMD:STYLE:", block=True))
    app_.add_handler(CallbackQueryHandler(donate_handlers.on_callback, pattern=r"^DONATE:", block=True))

    # Универсальный роутер callback’ов онбординга/режимов — НЕ трогаем чужие префиксы
    app_.add_handler(
        CallbackQueryHandler(
            handle_callback_query,
            pattern=r"^(?!(open:|SETTINGS:|SET:|CMD:(LANG|LEVEL|STYLE):|htp_|DONATE:))",
        ),
        group=1,
    )

    # Лимит-гейт — команды сюда не попадают
    app_.add_handler(
        MessageHandler((filters.TEXT & ~filters.COMMAND) | filters.VOICE | filters.AUDIO, usage_gate),
        group=0,
    )

    # Основной диалог — команды сюда не попадают
    app_.add_handler(
        MessageHandler((filters.TEXT & ~filters.COMMAND) | filters.VOICE | filters.AUDIO, handle_message),
        group=1,
    )

# -------------------------------------------------------------------------
# Инициализация
# -------------------------------------------------------------------------
def init_databases():
    init_profiles_db()
    init_usage_db()
    init_training_db()

@app.on_event("startup")
async def on_startup():
    init_databases()
    setup_handlers(bot_app)
    await bot_app.initialize()
    await bot_app.start()
    logger.info("Bot application is ready")

@app.on_event("shutdown")
async def on_shutdown():
    await bot_app.stop()
    await bot_app.shutdown()
    logger.info("Bot application is stopped")

@app.get("/")
async def root():
    return {"ok": True, "service": "english-talking-bot"}
