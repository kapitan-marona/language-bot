from __future__ import annotations
import os
import logging
import asyncio
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

# Переводчик (старые команды остаются)
from handlers.commands.translator_cmd import translator_on_command, translator_off_command
from handlers.translator_mode import handle_translator_callback

from handlers.callbacks.menu import menu_router
from handlers.callbacks import how_to_pay_game

# Онбординг
from components.onboarding import send_onboarding, append_tr_callback

from components.profile_db import init_db as init_profiles_db, get_all_chat_ids
from components.usage_db import init_usage_db

# Старые команды настройки (ПОКА оставляем)
from handlers.commands.language_cmd import language_command, language_on_callback
from handlers.commands.level_cmd import level_command, level_on_callback
from handlers.commands.style_cmd import style_command, style_on_callback

from handlers.commands.privacy import privacy_command, delete_me_command
from handlers.commands.db_info import db_info_command
from handlers.commands.db_health import db_health_command

from handlers.commands import admin_cmds

# NEW: напоминания
from components.reminders import run_nudges

# Админка
from handlers.admin.menu import admin_menu, admin_callback
from handlers.admin.promo_adm import promo_text_handler
from handlers.admin.price_adm import price_text_handler
from handlers.admin.test_lang import test_lang_command

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

# защита внутренних ручек
ADMIN_PANEL_TOKEN = os.getenv("ADMIN_PANEL_TOKEN")
ENV = os.getenv("ENV", "dev")

# Логирование
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.INFO)
logging.getLogger("telegram").setLevel(logging.INFO)

logger = logging.getLogger("english-bot")

app = FastAPI(title="English Talking Bot")
bot_app: Application = Application.builder().token(TELEGRAM_TOKEN).build()

# -------------------------------------------------------------------------
# Утилиты
# -------------------------------------------------------------------------
def fire_and_forget(coro, *, name: str = "task"):
    task = asyncio.create_task(coro, name=name)

    def _done(t: asyncio.Task):
        try:
            exc = t.exception()
        except asyncio.CancelledError:
            return
        if exc:
            logger.exception("Background task %s failed: %s", name, exc)

    task.add_done_callback(_done)
    return task


def _check_admin_token(req: Request) -> bool:
    if ENV == "prod":
        token = req.headers.get("X-Admin-Token") or req.query_params.get("token")
        return bool(token and ADMIN_PANEL_TOKEN and token == ADMIN_PANEL_TOKEN)
    return True


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
            return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)

    data = await req.json()
    update = Update.de_json(data, bot_app.bot)
    fire_and_forget(bot_app.process_update(update))
    return {"ok": True}


@app.get("/set_webhook")
async def set_webhook(request: Request, url: Optional[str] = Query(default=None)):
    if not _check_admin_token(request):
        return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)

    target = url or (f"{PUBLIC_URL.rstrip('/')}/{WEBHOOK_SECRET_PATH}" if PUBLIC_URL else None)
    ok = await bot_app.bot.set_webhook(
        url=target,
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query", "pre_checkout_query"],
        secret_token=TELEGRAM_WEBHOOK_SECRET_TOKEN or None,
    )
    return {"ok": ok, "url": target}


# -------------------------------------------------------------------------
# Хендлеры
# -------------------------------------------------------------------------
def setup_handlers(app_: "Application"):
    app_.add_error_handler(on_error)

    # === Основные команды ===
    app_.add_handler(CommandHandler("start", lambda u, c: send_onboarding(u, c)))
    app_.add_handler(CommandHandler("help", help_command))
    app_.add_handler(CommandHandler("buy", buy_command))
    app_.add_handler(CommandHandler("promo", promo_command))
    app_.add_handler(CommandHandler("donate", donate_command))

    # настройки
    app_.add_handler(CommandHandler("settings", settings.cmd_settings))

    # ✅ NEW: быстрые команды меню Telegram
    app_.add_handler(CommandHandler("voice", settings.cmd_voice))
    app_.add_handler(CommandHandler("text", settings.cmd_text))

    # переводчик (старые + новые алиасы)
    app_.add_handler(CommandHandler("translator_on", translator_on_command))
    app_.add_handler(CommandHandler("translator_off", translator_off_command))

    app_.add_handler(CommandHandler("translation", translator_on_command))  # ✅ alias
    app_.add_handler(CommandHandler("chat", translator_off_command))        # ✅ alias

    # === Старые команды языка/уровня/стиля (ПОКА оставляем) ===
    app_.add_handler(CommandHandler("language", language_command))
    app_.add_handler(CommandHandler("level", level_command))
    app_.add_handler(CommandHandler("style", style_command))

    # privacy
    app_.add_handler(CommandHandler("privacy", privacy_command))
    app_.add_handler(CommandHandler("delete_me", delete_me_command))

    # платежи
    app_.add_handler(PreCheckoutQueryHandler(precheckout_ok))
    app_.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_successful_payment))

    # callback-и
    app_.add_handler(CallbackQueryHandler(menu_router, pattern=r"^open:", block=True))
    app_.add_handler(CallbackQueryHandler(append_tr_callback, pattern=r"^append_tr:(yes|no)$"))
    app_.add_handler(CallbackQueryHandler(settings.on_callback, pattern=r"^(SETTINGS:|SET:)", block=True))

    # Старые CMD callbacks (позже уберём)
    app_.add_handler(CallbackQueryHandler(language_on_callback, pattern=r"^CMD:LANG:", block=True))
    app_.add_handler(CallbackQueryHandler(level_on_callback, pattern=r"^CMD:LEVEL:", block=True))
    app_.add_handler(CallbackQueryHandler(style_on_callback, pattern=r"^CMD:STYLE:", block=True))

    # Translator callbacks
    app_.add_handler(CallbackQueryHandler(handle_translator_callback, pattern=r"^TR:", block=True))

    # Универсальный роутер онбординга
    app_.add_handler(CallbackQueryHandler(handle_callback_query), group=1)

    # usage gate + основной диалог
    app_.add_handler(
        MessageHandler((filters.TEXT & ~filters.COMMAND) | filters.VOICE | filters.AUDIO, usage_gate),
        group=0,
    )
    app_.add_handler(
        MessageHandler((filters.TEXT & ~filters.COMMAND) | filters.VOICE | filters.AUDIO, handle_message),
        group=1,
    )


# -------------------------------------------------------------------------
# Startup / Shutdown
# -------------------------------------------------------------------------
def init_databases():
    init_profiles_db()
    init_usage_db()


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
