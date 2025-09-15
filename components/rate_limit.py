# components/rate_limit.py
import asyncio
import time
from functools import wraps

from telegram.ext import ContextTypes

def async_rate_limit(seconds: float):
    """
    Декоратор для PTB v20+ (async handlers).
    Хранит таймстемп в context.chat_data["__last_ts"].
    При превышении лимита — отправляет короткий ответ и НЕ вызывает хендлер.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            chat_data = context.chat_data
            now = time.time()
            last_ts = chat_data.get("__last_ts", 0.0)
            if (now - last_ts) < seconds:
                # мягко и быстро отвечаем, не блокируя основной обработчик
                try:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text="⏳ Погоди, думаю 🙂")
                finally:
                    return
            chat_data["__last_ts"] = now
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator
