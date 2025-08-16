"""# 🇬🇧 English Talking Bot

> Многофункциональный Telegram-бот для практики английского языка в тексте и голосе — с онбордингом, промокодами, подпиской через Stars и режимом обучения (teach).

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-success)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Возможности

- 💬 **Диалог с ИИ** — текстом или голосом (TTS/ASR через OpenAI)
- 🎙 **Голосовой режим** — бот отвечает голосом, можно «озвучить» реплику
- 🆕 **Онбординг** — выбор языка интерфейса, целевого языка/уровня/стиля
- 💳 **Подписка** через **Telegram Stars** (XTR) + уведомления об оплате
- 🎟 **Промокоды** — снимают лимит сообщений на день
- 📚 **Режим обучения** `/teach` — добавляй свои пары «фраза — перевод»
- ⏸ **Пауза диалога на время /teach** + кнопка **▶️ Продолжить**
- 📊 **Лимит** бесплатных сообщений (по умолчанию 15/день) + мягкие напоминания
- ⚙ **Настройки**: язык/уровня/стиль — кнопки и команды `/language`, `/level`, `/style`
- 🧠 **Мягкая корректировка ошибок** — стиль/уровень-aware, без терминов
- 🌍 **i18n** — единый резолвер языка интерфейса, шорткоды языков `/codes`
- 🛠 **Лёгкая расширяемость** — добавить команду/режим за минуты

---

## 🏗 Архитектура (в двух словах)

- **FastAPI** принимает вебхук Telegram → `english_bot.py`.
- Апдейты отдаются в `python-telegram-bot` (**PTB v20+**) — **асинхронно** через `asyncio.create_task`, чтобы не блокировать вебхук.
- Хендлеры разделены по группам:
  - **group=0**: промо-роутер онбординга → лимит-гейт `usage_gate`
  - **group=1**: «шлюз-пауза» `/teach` → основной диалог `handle_message`
- Платежи **Stars**: выставляем счёт `send_invoice`, ловим `PreCheckoutQuery` и `SUCCESSFUL_PAYMENT`.
- Состояние онбординга хранится в `state.session.user_sessions`, профиль/лимиты/глоссарий — в лёгких SQLite-таблицах.

---

## 🚀 Установка и запуск

### 1) Клонирование
```bash
git clone https://github.com/username/english-talking-bot.git
cd english-talking-bot
```

### 2) Зависимости
```bash
python -m venv .venv
source .venv/bin/activate    # macOS/Linux
# .venv\Scripts\activate     # Windows (PowerShell)
pip install -r requirements.txt
```

### 3) Переменные окружения

Создайте файл `.env` в корне проекта:

```env
# Telegram
TELEGRAM_TOKEN=123456:ABC...           # токен бота от @BotFather (обязательно)
WEBHOOK_SECRET_PATH=Dlzfd1hw_jm76...   # секретный путь вебхука, любая случайная строка (обязательно)
TELEGRAM_WEBHOOK_SECRET_TOKEN=s3cr3t   # секрет заголовка вебхука (желательно)

# Внешний адрес вашего сервиса
PUBLIC_URL=https://your-domain.tld     # например: https://english-bot.onrender.com (обязательно для /set_webhook)

# OpenAI
OPENAI_API_KEY=sk-...                  # для генерации текста/голоса (если используете голос/чат через OpenAI)
```

> Почему два секрета?  
> • `WEBHOOK_SECRET_PATH` прячет сам путь (`/{secret}`),  
> • `TELEGRAM_WEBHOOK_SECRET_TOKEN` — валидирует заголовок `X-Telegram-Bot-Api-Secret-Token`.  
> Вместе они надёжно закрывают ваш вебхук.

### 4) Локальный запуск
```bash
uvicorn english_bot:app --host 0.0.0.0 --port 8000 --reload
```

Настройте вебхук (бот должен видеть ваш публичный адрес). Если у вас нет домена, можно использовать ngrok/Cloudflare Tunnel:

```bash
# Пример (если PUBLIC_URL уже указывает на ваш туннель)
curl "http://localhost:8000/set_webhook"
```

Проверка здоровья:
```bash
curl "http://localhost:8000/healthz"
# {"ok": true}
```

---

## ☁ Деплой на Render

### Вариант 1. Через Dashboard
1. **New → Web Service** → подключите репозиторий.
2. Runtime: **Python 3.11+**.
3. Build Command:
   ```bash
   pip install -r requirements.txt
   ```
4. Start Command (рекомендуется с `$PORT`):
   ```bash
   uvicorn english_bot:app --host 0.0.0.0 --port $PORT
   ```
5. Добавьте переменные окружения из `.env` в **Environment**.
6. После деплоя откройте в браузере:
   ```
   https://<your-service>.onrender.com/set_webhook
   ```

### Вариант 2. Через `render.yaml`
```yaml
services:
  - type: web
    name: english-talking-bot
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn english_bot:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: TELEGRAM_TOKEN
      - key: WEBHOOK_SECRET_PATH
      - key: PUBLIC_URL
      - key: TELEGRAM_WEBHOOK_SECRET_TOKEN
      - key: OPENAI_API_KEY
    plan: Professional
```

> Совет: поменяйте `PUBLIC_URL` на точный адрес сервиса на Render (https://…onrender.com).  
> В логах должен появиться `Uvicorn running on http://0.0.0.0:<port>` и `Application started`.

---

## 📂 Структура проекта

```
.
├── english_bot.py               # FastAPI + Telegram Application + регистрация хендлеров
├── handlers/
│   ├── chat/
│   │   ├── chat_handler.py      # основной диалог с Мэттом
│   │   └── prompt_templates.py  # промпты/правила коррекции/вводные
│   ├── commands/
│   │   ├── help.py              # /help (локализованные подсказки)
│   │   ├── payments.py          # /buy (Stars invoice)
│   │   ├── promo.py             # /promo <code>
│   │   ├── donate.py            # /donate [amount] + пресеты
│   │   ├── language_cmd.py      # /language
│   │   ├── level_cmd.py         # /level
│   │   ├── style_cmd.py         # /style
│   │   ├── consent.py           # /consent, /codes (пояснение и список кодов)
│   │   ├── teach.py             # /teach (режим обучения + пауза диалога)
│   │   └── reset.py             # /reset (если используете)
│   ├── callbacks/
│   │   ├── menu.py              # меню/настройки
│   │   └── how_to_pay_game.py   # геймифицированная подсказка оплаты
│   └── middleware/
│       └── usage_gate.py        # лимит бесплатных сообщений + промо-гейт
├── components/
│   ├── gpt_client.py            # AsyncOpenAI (чат/tts)
│   ├── payments.py              # Stars (invoice/precheckout/success)
│   ├── onboarding.py            # онбординг + promo_code_message
│   ├── profile_db.py            # профиль пользователя (SQLite)
│   ├── usage_db.py              # счётчик сообщений (SQLite)
│   ├── training_db.py           # глоссарий teach (SQLite)
│   ├── i18n.py                  # единый резолвер языка интерфейса
│   └── lang_codes.py            # словарь ISO-639-1 для /codes
├── state/
│   └── session.py               # in-memory сессии онбординга
├── requirements.txt
└── README.md
```

> БД — лёгкие SQLite-файлы, создаются автоматически при первом запуске (внешняя СУБД не нужна).

---

## ⚙️ Переменные/настройки (кратко)

| Переменная | Назначение | Обязательно |
|---|---|---|
| `TELEGRAM_TOKEN` | токен бота из @BotFather | ✅ |
| `WEBHOOK_SECRET_PATH` | секретный путь вебхука (`/{secret}`) | ✅ |
| `PUBLIC_URL` | публичный адрес сервиса (для `/set_webhook`) | ✅ |
| `TELEGRAM_WEBHOOK_SECRET_TOKEN` | секрет заголовка вебхука | желат. |
| `OPENAI_API_KEY` | ключ OpenAI (чат/tts) | при голосе/чате |

> Лимиты/порог (`FREE_DAILY_LIMIT=15`, `REMIND_AFTER=10`) заданы в `usage_gate.py`. При желании можно вынести в ENV.

---

## 💡 Команды бота

| Команда | Что делает |
|---|---|
| `/start` | онбординг (выбор языка интерфейса → промокод → привет от Мэтта) |
| `/help` | справка, команды и советы по общению |
| `/settings` | настройка языка/уровня/стиля (кнопки) |
| `/language`, `/level`, `/style` | быстрые изменения одного параметра |
| `/buy` | счёт на 30 дней (Stars / XTR) |
| `/promo <код>` | активировать промокод |
| `/donate [сумма]` | быстрый донат в Stars (или пресеты) |
| `/teach` | режим обучения (пары «фраза — перевод», сохраняются в `/glossary`) |
| `/glossary` | список сохранённых пар |
| `/consent` / `/codes` | инфо о режиме обучения / список кодов языков |
| `/reset` | сброс контекста (опционально ограничить админом) |

---

## 🗣 Мягкая корректировка ошибок

- бот **исправляет только то**, что мешает пониманию (без теории/терминов);  
- формулировка и детализация зависят от **уровня** (A0–C2) и **стиля** (casual/business);  
- для A0–A2 — допускается поддержка на языке интерфейса;  
- при явном запросе «объясни подробно» — боту снижается temperature и включается разъяснительный регистр.

Настройки/правила собраны в `handlers/chat/prompt_templates.py`.

---

## 🧩 Как добавить свою команду

1) Создайте файл в `handlers/commands/`:
```python
from telegram import Update
from telegram.ext import ContextTypes

async def my_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Это новая команда.")
```

2) Зарегистрируйте в `english_bot.py`:
```python
from handlers.commands.my import my_command
app_.add_handler(CommandHandler("my", my_command))
```

Готово — команда доступна.

---

## 🛠 Отладка и проверка

- **Вебхук**: откройте `https://<host>/set_webhook` (возвращает `{"ok": true, "url": ...}`).
- **Хелсчеки**: `GET /healthz` → `{"ok": true}`.
- **Логи**: Render → вкладка **Logs**; локально — stdout.
- **Частые предупреждения**:
  - `Forbidden: bad webhook secret token` — проверьте `TELEGRAM_WEBHOOK_SECRET_TOKEN` на стороне бота и вебхука.
  - `Unhandled callback_data` — кнопка пришла не на тот паттерн; проверьте `pattern` ваших `CallbackQueryHandler`.
- **Проблемы с «нет» на промокоде**: убедитесь, что включён роутер `promo_stage_router` (см. `english_bot.py`, group=0).
- **Пауза в /teach**: если бот «молчит», нажмите **▶️ Продолжить** (снимет `chat_data["dialog_paused"]`).

---

## 🔐 Безопасность

- Никогда не храните токены в репозитории — используйте `.env` / переменные окружения.
- Делайте длинный случайный `WEBHOOK_SECRET_PATH` и включайте `TELEGRAM_WEBHOOK_SECRET_TOKEN`.
- Не логируйте приватные данные пользователей/платежей.
- Обновляйте зависимости (`requirements.txt`) регулярно.

---

## 🤝 Вклад и поддержка

PR-ы и идеи приветствуются!  
Нашли проблему? Откройте **Issue** с шагами воспроизведения и логами (без токенов).

---

## 📜 Лицензия

MIT © 2025 — Сделано с ❤️"""

from __future__ import annotations
import os
import logging
import asyncio  # неблокирующая обработка апдейтов
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
from state.session import user_sessions

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    ApplicationHandlerStop,
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
    resume_chat_callback,   # NEW
)
from handlers.callbacks.menu import menu_router
from handlers.callbacks import how_to_pay_game

# Онбординг и сброс
from handlers.commands.reset import reset_command
from components.onboarding import send_onboarding, promo_code_message

from components.profile_db import init_db as init_profiles_db
from components.usage_db import init_usage_db
from components.training_db import init_training_db

from handlers.commands.language_cmd import language_command, language_on_callback
from handlers.commands.level_cmd import level_command, level_on_callback
from handlers.commands.style_cmd import style_command, style_on_callback
from handlers.commands.consent import consent_info_command, codes_command  # уже были
from components.i18n import get_ui_lang

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
        asyncio.create_task(bot_app.process_update(update))  # неблокирующе
    except Exception as e:
        logger.exception("Webhook handling error: %s", e)
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
# «Шлюз-пауза»: если включён teach-пауза — не пускаем в обычный диалог
# -------------------------------------------------------------------------
def _resume_kb_text(ui: str) -> InlineKeyboardMarkup:
    txt = "▶️ Продолжить" if ui == "ru" else "▶️ Resume"
    return InlineKeyboardMarkup([[InlineKeyboardButton(txt, callback_data="TEACH:RESUME")]])

async def paused_gate(update: Update, ctx):
    if ctx.chat_data.get("dialog_paused"):
        ui = get_ui_lang(update, ctx)
        msg = ("Сейчас активен режим /teach. Нажми кнопку, чтобы вернуться к разговору."
               if ui == "ru"
               else "Teaching mode is active. Tap the button to resume the chat.")
        await (update.effective_message or update.message).reply_text(msg, reply_markup=_resume_kb_text(ui))
        # Полностью останавливаем обработку этого апдейта (чтобы не дошло до handle_message)
        raise ApplicationHandlerStop

async def promo_stage_router(update: Update, ctx):
    """Перехватывает текст, когда ждём ввод промокода на онбординге."""
    try:
        session = user_sessions.setdefault(update.effective_chat.id, {})
    except Exception:
        session = {}
    if session.get("onboarding_stage") == "awaiting_promo":
        await promo_code_message(update, ctx)
        # чтобы дальше не пошло ни в usage_gate, ни в handle_message
        raise ApplicationHandlerStop

# -------------------------------------------------------------------------
# Хендлеры
# -------------------------------------------------------------------------
def setup_handlers(app_: "Application"):
    app_.add_error_handler(on_error)

    # Команды
    app_.add_handler(CommandHandler("start", lambda u, c: send_onboarding(u, c)))
    app_.add_handler(CommandHandler("help", help_command))
    app_.add_handler(CommandHandler("buy", buy_command))
    app_.add_handler(CommandHandler("promo", promo_command))
    app_.add_handler(CommandHandler("donate", donate_command))
    app_.add_handler(CommandHandler("settings", settings.cmd_settings))
    app_.add_handler(CommandHandler("language", language_command))
    app_.add_handler(CommandHandler("level", level_command))
    app_.add_handler(CommandHandler("style", style_command))
    app_.add_handler(CommandHandler("consent", consent_info_command))
    app_.add_handler(CommandHandler("codes", codes_command))
    app_.add_handler(CommandHandler("consent_on", consent_on))
    app_.add_handler(CommandHandler("consent_off", consent_off))
    app_.add_handler(CommandHandler("glossary", glossary_cmd))
    app_.add_handler(build_teach_handler())

    # Платежи Stars
    app_.add_handler(PreCheckoutQueryHandler(precheckout_ok))
    app_.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_successful_payment))

    # DONATE: числовой ввод — блокируем дальнейшие хендлеры в группе 0
    from handlers.commands import donate as donate_handlers
    app_.add_handler(
        MessageHandler(filters.Regex(r"^\s*\d{1,5}\s*$"), donate_handlers.on_amount_message, block=True),
        group=0,
    )

    # Callback’и меню, настроек, how-to-pay + наша кнопка возобновления
    app_.add_handler(CallbackQueryHandler(menu_router, pattern=r"^open:", block=True))
    app_.add_handler(CallbackQueryHandler(settings.on_callback, pattern=r"^(SETTINGS:|SET:)", block=True))
    app_.add_handler(CallbackQueryHandler(how_to_pay_game.how_to_pay_entry, pattern=r"^htp_start$", block=True))
    app_.add_handler(CallbackQueryHandler(how_to_pay_game.how_to_pay_how, pattern=r"^htp_how$", block=True))
    app_.add_handler(CallbackQueryHandler(how_to_pay_game.how_to_pay_exit, pattern=r"^htp_exit$", block=True))
    app_.add_handler(CallbackQueryHandler(how_to_pay_game.how_to_pay_go_buy, pattern=r"^htp_buy$", block=True))
    app_.add_handler(CallbackQueryHandler(language_on_callback, pattern=r"^CMD:LANG:", block=True))
    app_.add_handler(CallbackQueryHandler(level_on_callback, pattern=r"^CMD:LEVEL:", block=True))
    app_.add_handler(CallbackQueryHandler(style_on_callback, pattern=r"^CMD:STYLE:", block=True))
    app_.add_handler(CallbackQueryHandler(resume_chat_callback, pattern=r"^TEACH:RESUME$", block=True))  # NEW

    # Универсальный роутер callback’ов — исключаем наши префиксы
    app_.add_handler(
        CallbackQueryHandler(
            handle_callback_query,
            pattern=r"^(?!(open:|SETTINGS:|SET:|CMD:(LANG|LEVEL|STYLE):|htp_|DONATE:|TEACH:RESUME))",
        ),
        group=1,
    )

    # Группа 0 — гейт лимитов/промо и пр.
    app_.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, promo_stage_router),
        group=0,
    )

    app_.add_handler(
        MessageHandler((filters.TEXT & ~filters.COMMAND) | filters.VOICE | filters.AUDIO, usage_gate),
        group=0,
    )

    # Группа 1 — наш «шлюз-пауза»
    app_.add_handler(
        MessageHandler((filters.TEXT & ~filters.COMMAND) | filters.VOICE | filters.AUDIO, paused_gate),
        group=1,
    )

    # Группа 1 — основной диалог
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
