# components/gpt_client.py
import os
import re
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


# ---------- ВСПОМОГАТЕЛЬНЫЕ ДЕТЕКТОРЫ ----------

_LEVEL_RE = re.compile(r"\('(A0|A1|A2|B1|B2|C1|C2)'\)")

_DETAIL_KWS = [
    # RU
    "исправь подробно", "исправьте подробно",
    "объясни ошибки", "объясните ошибки",
    "объясни мою ошибку", "объясни мои ошибки",
    "объясни правило", "объясните правило",
    "объясни правила", "объясните правила",
    "разбор ошибок", "разберите ошибки",
    # EN
    "explain mistakes", "explain my mistakes",
    "explain the mistakes", "explain mistake",
    "explain rule", "explain the rule", "explain rules",
    "correct in detail", "fix in detail",
]

def _detect_level_from_messages(messages: List[Dict[str, Any]]) -> str | None:
    """
    Пытаемся вытащить уровень из системного промпта (см. prompt_templates: "('A1')" и т.п.).
    Возвращает 'A0'..'C2' или None.
    """
    try:
        for m in messages or []:
            if (m.get("role") or "").lower() != "system":
                continue
            content = (m.get("content") or "")
            mobj = _LEVEL_RE.search(content)
            if mobj:
                return mobj.group(1)
    except Exception:
        pass
    return None

def _is_detailed_explain_requested(messages: List[Dict[str, Any]]) -> bool:
    """
    Проверяем последнее пользовательское сообщение на запрос "подробного объяснения".
    """
    try:
        for m in reversed(messages or []):
            if (m.get("role") or "").lower() == "user":
                txt = (m.get("content") or "").lower()
                return any(kw in txt for kw in _DETAIL_KWS)
    except Exception:
        pass
    return False


def _choose_temperature(messages: List[Dict[str, Any]]) -> float:
    """
    Схема:
      A0–A2 → 0.5
      B1–C2 → 0.65
      Детальный разбор → 0.5 (A0–A2) / 0.45 (B1–C2)
      Фолбэк (уровень не найден) → 0.6
    """
    level = _detect_level_from_messages(messages)
    detail = _is_detailed_explain_requested(messages)

    if level is None:
        # надежный нейтральный фолбэк
        temp = 0.6
        logger.info("ask_gpt: temperature=%s (fallback, detail=%s)", temp, detail)
        return 0.5 if (detail and False) else temp  # detail без уровня не понижаем

    low = level in ("A0", "A1", "A2")
    if detail:
        temp = 0.5 if low else 0.45
    else:
        temp = 0.5 if low else 0.65

    logger.info("ask_gpt: temperature=%s (level=%s, detail=%s)", temp, level, detail)
    return temp


# ---------- ОСНОВНАЯ ФУНКЦИЯ ----------

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

    temperature = _choose_temperature(sanitized)

    async def _call():
        return await client.chat.completions.create(
            model=model,
            messages=sanitized,
            temperature=temperature,
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
