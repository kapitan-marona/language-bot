# 🇬🇧 English Talking Bot

> Многофункциональный Telegram-бот для практики английского языка в тексте и голосе, с онбордингом, промокодами, подпиской и режимом обучения.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-success)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Возможности

- 💬 **Диалог с ИИ** — текстом или голосом
- 🎙 **Голосовой режим** — бот отвечает аудиосообщениями
- 🆕 **Онбординг** — первый запуск с выбором языка интерфейса и целей
- 💳 **Подписка** через **Telegram Stars**
- 🎟 **Промокоды** для снятия лимитов
- 📚 **Режим обучения** (`/teach`) для исправления ошибок
- 📊 **Лимит бесплатных сообщений** (15 в день) с напоминанием
- ⚙ **Меню настроек** с кнопками
- 🛠 Легко расширяется новыми командами и функциями

---

## 🚀 Установка и запуск

### 1. Клонирование репозитория
```bash
git clone https://github.com/username/english-talking-bot.git
cd english-talking-bot
```

### 2. Установка зависимостей
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 3. Настройка переменных окружения
Создайте `.env` в корне проекта:
```env
TELEGRAM_TOKEN=ваш_токен_бота
WEBHOOK_SECRET_PATH=секретный_путь
PUBLIC_URL=https://ваш-домен
TELEGRAM_WEBHOOK_SECRET_TOKEN=секрет_вебхука
```

### 4. Запуск локально
```bash
uvicorn english_bot:app --host 0.0.0.0 --port 8000 --reload
```

---

## ☁ Деплой на Render

1. Создайте новый **Web Service** на [Render](https://render.com/)
2. Укажите **Python 3.11+**
3. В переменные окружения добавьте всё из `.env`
4. Команда запуска:
```bash
uvicorn english_bot:app --host 0.0.0.0 --port 10000
```
5. После деплоя откройте `/set_webhook` в браузере:
```
https://ваш-домен/set_webhook
```

---

## 📂 Структура проекта

```
.
├── english_bot.py             # Основной входной файл FastAPI + Telegram
├── handlers/                  # Хендлеры команд, сообщений, кнопок
│   ├── commands/               # Логика /команд
│   ├── callbacks/              # Обработка inline-кнопок
│   ├── chat/                   # Основной диалог с ботом
│   └── middleware/             # Промежуточная логика (лимиты и т.д.)
├── components/                 # Логика работы (БД, промо, платежи)
├── state/                      # Хранилище сессий
├── utils/                      # Утилиты и декораторы
├── requirements.txt            # Зависимости
└── README.md                   # Этот файл
```

---

## 💡 Основные команды бота

| Команда         | Описание |
|-----------------|----------|
| `/start`        | Запуск онбординга |
| `/help`         | Список команд |
| `/buy`          | Купить подписку |
| `/donate`       | Донат |
| `/promo <код>`  | Ввести промокод |
| `/settings`     | Настройки |
| `/teach`        | Режим обучения |
| `/glossary`     | Словарь |
| `/reset`        | Сброс сессии |

---

## 🧩 Как добавить команду

1. Создай файл в `handlers/commands/`:
```python
from telegram import Update
from telegram.ext import ContextTypes

async def my_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Это новая команда.")
```
2. Зарегистрируй в `english_bot.py`:
```python
app_.add_handler(CommandHandler("my", my_command))
```

---

## 🛠 Отладка

- Проверить вебхук:
```
GET /set_webhook
```
- Логи в Render: вкладка **Logs**
- Локально: запусти с `--reload` для автообновления

---

## 📜 Лицензия

MIT © 2025 — Сделано с ❤️
