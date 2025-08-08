import os
import logging
import asyncio
from typing import List, Dict, Any
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

async def _retry(coro_factory, attempts: int = 2, delay_sec: float = 0.6):
    """
    Простой асинхронный ретрай без внешних зависимостей.
    coro_factory: функция без аргументов, возвращает корутину.
    """
    last_exc = None
    for i in range(attempts):
        try:
            return await coro_factory()
        except Exception as e:
            last_exc = e
            logger.warning("ask_gpt retry %s/%s due to %s", i + 1, attempts, e)
            await asyncio.sleep(delay_sec)
    raise last_exc

# Основная функция для работы с GPT
async def ask_gpt(messages: List[Dict[str, Any]], model: str = "gpt-3.5-turbo") -> str:
    """
    Делает асинхронный запрос к OpenAI GPT API.

    :param messages: List[Dict], история сообщений для ChatCompletion.
    :param model: str, модель GPT (по умолчанию gpt-3.5-turbo; можно 'gpt-4o').
    :return: str, сгенерированный ответ.
    """
    if not client:
        logger.error("OPENAI_API_KEY is missing")
        return "⚠️ Ошибка конфигурации: отсутствует ключ OpenAI."

    # Санитизация сообщений: обрежем слишком длинные контенты
    sanitized: List[Dict[str, Any]] = []
    for m in messages or []:
        role = m.get("role", "user")
        content = (m.get("content") or "").strip()
        if len(content) > 4000:
            content = content[:4000]
        sanitized.append({"role": role, "content": content})

    async def _call():
        return await client.chat.completions.create(
            model=model,
            messages=sanitized,
            temperature=0.7,
            max_tokens=700,
        )

    try:
        # Небольшой ретрай на сетевые/эфемерные сбои
        response = await _retry(_call, attempts=2, delay_sec=0.7)
        text = (response.choices[0].message.content or "").strip()
        return text or "…"
    except Exception:
        logger.exception("[GPT ERROR]")
        return "⚠️ Ошибка генерации ответа. Попробуйте ещё раз!"
