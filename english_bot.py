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

# Новое: текст согласия (/consent)
from handlers.commands.consent import consent_info_command, codes_command

# Новое: админы для ограничения /reset
from components.admins import ADMIN_IDS
from components.i18n import get_ui_lang  # для сообщений об ограничении

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

# Новое: защита внутренних ручек и режим окружения
ADMIN_PANEL_TOKEN = os.getenv("ADMIN_PANEL_TOKEN")
ENV = os.getenv("ENV", "dev")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("english-bot")

app = FastAPI(title="English Talking Bot")
bot_app: Application = Application.builder().token(TELEGRAM_TOKEN).build()

# -------------------------------------------------------------------------
# Утилиты
# -------------------------------------------------------------------------
def fire_and_forget(coro, *, name: str = "task"):
    """Безопасный запуск фоновой задачи с логированием исключения."""
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
    """Проверка секрета для внутренних эндпоинтов (обязательна в prod)."""
    if ENV == "prod":
        token = req.headers.get("X-Admin-Token") or req.query_params.get("token")
        return bool(token and ADMIN_PANEL_TOKEN and token == ADMIN_PANEL_TOKEN)
    return True  # в dev разрешаем без токена

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
        # неблокирующе + с отлавливанием исключений
        fire_and_forget(bot_app.process_update(update), name=f"upd-{getattr(update, 'update_id', 'n/a')}")
    except Exception as e:
        logger.exception("Webhook handling error: %s", e)
        # всё равно даём 200, чтобы Telegram не дропал вебхук
        return JSONResponse({"ok": False, "error": "internal"}, status_code=200)
    return {"ok": True}

@app.get("/set_webhook")
async def set_webhook(request: Request, url: Optional[str] = Query(default=None)):
    if not _check_admin_token(request):
        return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)

    target = url or (f"{PUBLIC_URL.rstrip('/')}/{WEBHOOK_SECRET_PATH}" if PUBLIC_URL else None)
    if not target:
        return JSONResponse({"ok": False, "error": "PUBLIC_URL is not set"}, status_code=400)
    logger.info("Setting webhook to %s", target)
    ok = await bot_app.bot.set_webhook(
        url=target,
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query", "pre_checkout_query"],  # сузили список
        secret_token=TELEGRAM_WEBHOOK_SECRET_TOKEN or None,
    )
    return {"ok": ok, "url": target}

# -------------------------------------------------------------------------
# Ограничение /reset только для админов
# -------------------------------------------------------------------------
async def reset_admin_only(update: Update, ctx):
    uid = update.effective_user.id if update.effective_user else None
    if not uid or uid not in ADMIN_IDS:
        ui = get_ui_lang(update, ctx)
        msg = "Эта команда доступна только администратору." if ui == "ru" else "This command is only available to the admin."
        await update.effective_message.reply_text(msg)
        return
    await reset_command(update, ctx)

# -------------------------------------------------------------------------
# Хендлеры
# -------------------------------------------------------------------------
def setup_handlers(app_: "Application"):
    app_.add_error_handler(on_error)

    # Команды
    app_.add_handler(CommandHandler("start", lambda u, c: send_onboarding(u, c)))
    app_.add_handler(CommandHandler("reset", reset_admin_only))  # было reset_command
    app_.add_handler(CommandHandler("help", help_command))
    app_.add_handler(CommandHandler("buy", buy_command))
    app_.add_handler(CommandHandler("promo", promo_command))
    app_.add_handler(CommandHandler("donate", donate_command))
    app_.add_handler(CommandHandler("settings", settings.cmd_settings))
    app_.add_handler(CommandHandler("consent", consent_info_command))
    app_.add_handler(CommandHandler("codes", codes_command))  # НОВОЕ

    # быстрые команды
    app_.add_handler(CommandHandler("language", language_command))
    app_.add_handler(CommandHandler("level", level_command))
    app_.add_handler(CommandHandler("style", style_command))

    # Teach/Glossary/Consent
    app_.add_handler(CommandHandler("consent_on", consent_on))
    app_.add_handler(CommandHandler("consent_off", consent_off))
    app_.add_handler(CommandHandler("glossary", glossary_cmd))
    # >>> единственная новая настройка — блокируем, чтобы основной диалог не шёл параллельно
    app_.add_handler(build_teach_handler(), block=True, group=1)

    # Платежи Stars
    app_.add_handler(PreCheckoutQueryHandler(precheckout_ok))
    app_.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_successful_payment))

    # DONATE: числовой ввод — блокируем дальнейшие хендлеры
    from handlers.commands import donate as donate_handlers
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

    # Универсальный роутер callback’ов онбординга/режимов — исключаем наши префиксы
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
