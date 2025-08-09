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
from telegram import Update, ReplyKeyboardRemove, InlineKeyboardMarkup
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
from handlers.commands.help import help_command, help_callback

# настройки
from handlers.settings import on_callback as settings_callback, cmd_settings

# режимы
from components.mode import get_mode_keyboard, MODE_SWITCH_MESSAGES  # noqa: E401

# NEW: обработка текстового ввода промокодов
from components.profile_db import get_user_profile, set_user_promo  # NEW
from components.promo import normalize_code, check_promo_code, activate_promo  # NEW

# ✅ Инициализация базы данных профилей (один раз при запуске)
try:
    init_db()
    logger.info("Profile DB initialized")
except Exception:
    logger.exception("Failed to initialize Profile DB")

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
    url = os.getenv("PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL")
    return url.rstrip("/") if url else None


def _mask_secret(secret: str, keep: int = 4) -> str:
    if not secret:
        return ""
    if len(secret) <= keep * 2:
        return "•" * len(secret)
    return f"{secret[:keep]}{'•'*(len(secret)-2*keep)}{secret[-keep:]}"


async def _ensure_webhook(app_obj: Application, base_url: str) -> None:
    url = f"{base_url}/{WEBHOOK_SECRET_PATH}"
    masked = f"{base_url}/{_mask_secret(WEBHOOK_SECRET_PATH)}"
    try:
        ok = await app_obj.bot.set_webhook(
            url=url,
            drop_pending_updates=True,
            allowed_updates=["message", "edited_message", "callback_query"],
        )
        info = await app_obj.bot.get_webhook_info()
        logger.info(
            "set_webhook(%s) -> %s; has_url=%s; last_error_date=%s; last_error_message=%s",
            masked, ok, bool(info.url), getattr(info, "last_error_date", None), getattr(info, "last_error_message", None)
        )
    except Exception:
        logger.exception("Failed to set webhook to %s", masked)


# === Режимы (команда и колбэк) ===
async def mode_command(update: Update, context):
    ud = context.user_data
    current_mode = ud.get("mode", "text")
    ui_lang = ud.get("ui_lang", "ru")
    kb: InlineKeyboardMarkup = get_mode_keyboard(current_mode, ui_lang)
    await update.message.reply_text(
        "Выбери, как будем общаться:" if ui_lang == "ru" else "Choose how we chat:",
        reply_markup=kb,
    )

async def mode_callback(update: Update, context):
    q = update.callback_query
    await q.answer()
    data = (q.data or "")
    if not data.startswith("mode:"):
        return
    _, value = data.split(":", 1)
    context.user_data["mode"] = value
    ui_lang = context.user_data.get("ui_lang", "ru")
    msg = MODE_SWITCH_MESSAGES.get(value, {}).get(ui_lang, "OK")
    kb: InlineKeyboardMarkup = get_mode_keyboard(value, ui_lang)
    await q.edit_message_text(msg, reply_markup=kb)


@app.on_event("startup")
async def on_startup():
    global bot_app

    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is not set")
        return

    try:
        bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        bot_app.add_error_handler(on_error)

        # Импорт обработчика чата здесь — чтобы избежать циклических импортов
        from handlers.chat.chat_handler import handle_message

        # === Порядок ВАЖЕН ===
        # 1) Наши целевые CallbackQuery-хендлеры — с паттернами и block=True
        bot_app.add_handler(
            CallbackQueryHandler(help_callback, pattern=r"^HELP:OPEN:", block=True),
            group=0,
        )
        bot_app.add_handler(
            CallbackQueryHandler(settings_callback, pattern=r"^(SETTINGS|SET):", block=True),
            group=0,
        )
        bot_app.add_handler(
            CallbackQueryHandler(mode_callback, pattern=r"^mode:", block=True),
            group=0,
        )

        # 2) Команды
        bot_app.add_handler(CommandHandler("mode", mode_command))
        bot_app.add_handler(CommandHandler("settings", cmd_settings))
        bot_app.add_handler(CommandHandler("start", send_onboarding))
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

        # 2.5) Локальный обработчик ТОЛЬКО для текстового ввода промокода (раньше общего)
        async def _promo_text_handler(update: Update, context):  # NEW
            if not getattr(update, "message", None):
                return
            # перехватываем только когда явно ждём промокод
            if not context.user_data.get("awaiting_promo"):
                return

            # сбрасываем ожидание, чтобы не ловить обычные сообщения
            context.user_data["awaiting_promo"] = False

            code_raw = (update.message.text or "").strip()
            if not code_raw:
                return

            code = normalize_code(code_raw)
            chat_id = update.effective_chat.id
            profile = (get_user_profile(chat_id) or {}) | {"chat_id": chat_id}

            if not check_promo_code(code):
                ui = (profile.get("interface_lang") or "ru")
                await update.message.reply_text(
                    "Промокод не найден 😕" if ui == "ru" else "Promo code not found 😕"
                )
                return

            ok, reason = activate_promo(profile, code)
            if not ok and reason == "already_used":
                ui = (profile.get("interface_lang") or "ru")
                await update.message.reply_text(
                    "Промокод уже активирован ранее." if ui == "ru" else "Promo was already used."
                )
                return

            # сохранить промо в БД
            set_user_promo(
                chat_id=chat_id,
                code=code,
                promo_type=profile.get("promo_type"),
                activated_at=profile.get("promo_activated_at"),
                days=profile.get("promo_days"),
            )

            # ответ пользователю
            ui = (profile.get("interface_lang") or "ru")
            promo_type = profile.get("promo_type")
            days = profile.get("promo_days")

            if promo_type == "timed" and days:
                msg = "Промокод активирован! Включён тариф с ограниченным сроком." \
                      if ui == "ru" else "Promo activated! Timed plan is on."
            elif promo_type == "english_only":
                msg = "Промокод активирован! Бессрочно, только для английского." \
                      if ui == "ru" else "Promo activated! Permanent, English only."
            elif promo_type == "permanent":
                msg = "Промокод активирован! Бессрочный доступ." \
                      if ui == "ru" else "Promo activated! Permanent access."
            else:
                msg = "Промокод активирован!" if ui == "ru" else "Promo activated!"

            await update.message.reply_text(msg)

        bot_app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, _promo_text_handler),
            group=-1,  # выполняется раньше общего обработчика сообщений
        )

        # 3) Общий CallbackQuery-хендлер — в самый конец (fallback)
        bot_app.add_handler(CallbackQueryHandler(handle_callback_query), group=1)

        # 4) Сообщения (основной диалог)
        bot_app.add_handler(MessageHandler((filters.TEXT | filters.VOICE) & ~filters.COMMAND, handle_message))

        # 5) Мягко убираем любую ReplyKeyboard после /start
        async def _kill_kb(update, context):
            try:
                await update.message.reply_text("\u2063", reply_markup=ReplyKeyboardRemove())  # invis char
            except Exception:
                pass
        bot_app.add_handler(CommandHandler("start", _kill_kb), group=-1)

        await bot_app.initialize()
        await bot_app.start()
        logger.info("Telegram Application initialized & started")

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
    try:
        if bot_app:
            await bot_app.stop()
            await bot_app.shutdown()
            logger.info("Telegram Application stopped")
    except Exception:
        logger.warning("Failed to gracefully stop Telegram Application")

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
    global bot_app
    if bot_app is None:
        return JSONResponse({"ok": False, "error": "bot not ready"}, status_code=503)

    base = (url or _guess_public_url())
    if not base:
        return JSONResponse({"ok": False, "error": "no base url; set PUBLIC_URL or provide ?url="}, status_code=400)

    await _ensure_webhook(bot_app, base)
    return {"ok": True, "webhook_set_to": f"{base}/{_mask_secret(WEBHOOK_SECRET_PATH)}"}


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
        try:
            await bot_app.process_update(update)
        except RuntimeError as e:
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
