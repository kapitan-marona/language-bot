import base64
from openai import AsyncOpenAI  # ✅ заменено с OpenAI
from config.config import OPENAI_API_KEY
from openai.types.chat import ChatCompletion

# ✅ используем асинхронный клиент
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ✅ теперь асинхронная функция
async def ask_gpt(messages: list, model: str = "gpt-3.5-turbo") -> str:
    """
    Отправляет список сообщений в GPT и возвращает текст ответа.

    :param messages: список сообщений в формате [{"role": "user" / "assistant" / "system", "content": "текст"}]
    :param model: имя модели (по умолчанию gpt-3.5-turbo)
    :return: ответ GPT как строка
    """
    try:
        # === ЛОГГИРУЕМ ВХОДЯЩИЙ СПИСОК СООБЩЕНИЙ ===
        print("=== GPT MESSAGES ===")
        for m in messages:
            print(m)
        print("====================")
        
        # ✅ асинхронный вызов
        response: ChatCompletion = await client.chat.completions.create(
            model=model,
            messages=messages
        )

        # === ЛОГГИРУЕМ ОТВЕТ GPT ===
        gpt_reply = response.choices[0].message.content.strip()
        print("=== GPT REPLY ===")
        print(gpt_reply)
        print("=================")
        return gpt_reply

    except Exception as e:
        print(f"[GPT Error] {e}")
        return "⚠️ Ошибка при обращении к GPT."
