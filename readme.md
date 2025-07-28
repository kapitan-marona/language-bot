# 🤖 english_bot

Лёгкий Telegram-бот для практики иностранных языков: английского, французского, испанского и не только.
Поддерживает выбор уровня, стиля общения и голосовой/текстовый режим.

---

## 📋 Возможности

- Уровни: A1-A2 или B1-B2
- Стили общения: casual или formal
- Интерфейс на русском или английском языке
- Текстовый и голосовой режим общения
- GPT-4 и OpenAI Whisper для обработки сообщений

---

## 🛠️ Установка

1. Клонировать репозиторий:

```bash
git clone https://github.com/kapitan-marona/english_talking_bot.git
cd english_talking_bot
```

2. Установить зависимости:

```bash
pip install -r requirements.txt
```

3. Добавить `.env` файл с переменными:

```bash
OPENAI_API_KEY=your-openai-key
TELEGRAM_TOKEN=your-telegram-bot-token
GOOGLE_APPLICATION_CREDENTIALS=your-google-credentials.json
WEBHOOK_SECRET_PATH=your-custom-path
```

4. Запуск:

```bash
uvicorn english_bot:app --reload
```

---

Автор: Проект разработан @marrona
