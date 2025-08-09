import os
import base64
import tempfile
import logging

from config.logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

from handlers.error_handler import on_error

from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
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


def _guess_public_url() -> str | None:
    """
    Берём публичный URL из окружения.
    Приоритет: PUBLIC_URL > RENDER_EXTERNAL_URL
    Пример: https://english-talking-bot.onrender.com
    """
    url = os.getenv("PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL")
    if url:
        return url.rstrip("/")
    return None


def _mask_secret(secret: str, keep: int = 4) -> str:
    """
    Маскирует WEBHOOK_SECRET_PATH для логов/ответов.
    Пример: Dlzfd1hw_jm76qqCirdDtA -> Dlzf••••••••••••••••tA
    """
    if not secret:
        return ""
    if len(secret) <= keep * 2:
        return "•" * len(secret)
    return f"{secret[:keep]}{'•'*(len(secret)-2*keep)}{secret[-keep:]}"


async def _ensure_webhook(app_obj: Application, base_url: str) -> None:
    """
    Ставит вебхук на base_url/WEBHOOK_SECRET_PATH.
    В логах и ответах секрет НЕ раскрываем.
    """
    url = f"{base_url}/{WEBHOOK_SECRET_PATH}"
    masked = f"{base_url}/{_mask_secret(WEBHOOK_SECRET_PATH)}"
    try:
        ok = await app_obj.bot.set_webhook(
            url=url,
            drop_pending_updates=True,  # очищаем очередь после прошлых 500-ок
            allowed_updates=["message", "edited_message", "callback_query"]
        )
        info = await app_obj.bot.get_webhook_info()
        # Не логируем info.url (он содержит полный секрет), логируем только маску
        logger.info(
            "set_webhook(%s) -> %s; has_url=%s; last_error_date=%s; last_error_message=%s",
            masked, ok, bool(info.url), getattr(info, "last_error_date", None), getattr(info, "last_error_message", None)
        )
    except Exception:
        logger.exception("Failed to set webhook to %s", masked)


@app.on_event("startup")
async def on_startup():
    global bot_app

    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is not set")
        return

    try:
        bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        bot_app.add_error_handler(on_error)

        # Импорт обработчиков тут — чтобы не ловить циклические импорты
        from handlers.chat.chat_handler import handle_message

        # Регистрируем хендлеры
        bot_app.add_handler(MessageHandler((filters.TEXT | filters.VOICE) & ~filters.COMMAND, handle_message))
        bot_app.add_handler(CommandHandler("start", send_onboarding))
        bot_app.add_handler(CallbackQueryHandler(handle_callback_query))

        # Команды для админа
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

        # ⬇️ Ждём полную инициализацию и старт (важно!)
        await bot_app.initialize()
        await bot_app.start()
        logger.info("Telegram Application initialized & started")

        # ⬇️ Ставим вебхук автоматически (если знаем публичный URL)
        base_url = _guess_public_url()
        if base_url:
            await _ensure_webhook(bot_app, base_url)
        else:
            logger.warning("PUBLIC_URL/RENDER_EXTERNAL_URL not set — webhook not configured automatically")

    except Exception:
        logger.exception("Failed to initialize/start Telegram Application")


@app.on_event("shutdown")
async def on_shutdown():
    global _tmp_creds_path, bot_app
    # Останавливаем Application
    try:
        if bot_app:
            await bot_app.stop()
            await bot_app.shutdown()
            logger.info("Telegram Application stopped")
    except Exception:
        logger.warning("Failed to gracefully stop Telegram Application")

    # Чистим временный файл с кредами (если создавали)
    if _tmp_creds_path:
        try:
            os.remove(_tmp_creds_path)
            logger.info("Removed temp Google credentials file")
        except Exception:
            logger.warning("Failed to remove temp Google credentials file")
        _tmp_creds_path = None


@app.get("/")
async def root():
    return {"ok": True}


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/set_webhook")
async def set_webhook(url: str = Query(default=None, description="Base public URL, e.g. https://your-app.onrender.com")):
    """
    Ручная установка вебхука:
    - без параметра url берём PUBLIC_URL/RENDER_EXTERNAL_URL
    - с параметром url используем его как базовый
    Секрет не раскрываем в ответе/логах.
    """
    global bot_app
    if bot_app is None:
        return JSONResponse({"ok": False, "error": "bot not ready"}, status_code=503)

    base = (url or _guess_public_url())
    if not base:
        return JSONResponse({"ok": False, "error": "no base url; set PUBLIC_URL or provide ?url="}, status_code=400)

    await _ensure_webhook(bot_app, base)
    return {"ok": True, "webhook_set_to": f"{base}/{_mask_secret(WEBHOOK_SECRET_PATH)}"}


# Вебхук с секретом — сам маршрут содержит секрет, но мы его нигде не логируем.
@app.post(f"/{WEBHOOK_SECRET_PATH}")
async def telegram_webhook(req: Request):
    global bot_app
    if bot_app is None:
        logger.error("bot_app is None on webhook call")
        return JSONResponse({"ok": False, "error": "bot not ready"}, status_code=503)

    try:
        body = await req.json()
    except Exception:
        # Не выводим URL/путь запроса — там есть секрет
        logger.exception("Invalid JSON in webhook request")
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)

    try:
        update = Update.de_json(body, bot_app.bot)
        # Обрабатываем апдейт синхронно (без быстрого ACK)
        try:
            await bot_app.process_update(update)
        except RuntimeError as e:
            # Подстраховка: если вдруг не инициализирован — доинициализируем и повторим
            if "was not initialized via `Application.initialize`" in str(e):
                logger.warning("Lazy-initializing Application on first webhook")
                await bot_app.initialize()
                await bot_app.start()
                await bot_app.process_update(update)
            else:
                raise
        return {"ok": True}
    except Exception:
        logger.exception("Error while processing update")
        return JSONResponse({"ok": False, "error": "processing error"}, status_code=500)
