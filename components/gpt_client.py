# components/gpt_client.py
from __future__ import annotations

import os
import logging
from typing import Any, Dict, List

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def _filter_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Пропускаем только параметры, поддерживаемые Chat Completions.
    Лишние/None — отбрасываем, чтобы не падать на старых версиях SDK.
    """
    allowed = {
        "temperature",
        "top_p",
        "max_tokens",
        "frequency_penalty",
        "presence_penalty",
        "stop",
        # при желании можно расширить список
    }
    return {k: v for k, v in kwargs.items() if k in allowed and v is not None}


async def ask_gpt(
    messages: List[Dict[str, str]],
    model: str = "gpt-4o",
    **kwargs: Any,
) -> str:
    """
    Универсальная асинхронная обёртка над Chat Completions.
    Принимает безопасные именованные параметры (temperature, max_tokens и т.п.).
    Возвращает text content первого варианта.
    """
    if not _client:
        logger.error("OPENAI_API_KEY is missing: AsyncOpenAI client is not configured")
        return ""

    params = _filter_kwargs(kwargs)
    if params:
        # Немного логов, чтобы было видно, что именно прокинули
        logger.info(
            "ask_gpt: using model=%s, extra=%s",
            model,
            ", ".join(f"{k}={params[k]}" for k in sorted(params)),
        )
    else:
        logger.debug("ask_gpt: using model=%s (no extra params)", model)

    resp = await _client.chat.completions.create(
        model=model,
        messages=messages,
        **params,  # безопасно: только разрешённые ключи
    )
    return (resp.choices[0].message.content or "").strip()
