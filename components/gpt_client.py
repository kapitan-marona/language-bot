from openai import OpenAI
from config.config import OPENAI_API_KEY
from openai.types.chat import ChatCompletion

client = OpenAI(api_key=OPENAI_API_KEY)

# ✅ теперь асинхронная функция
async def ask_gpt(messages: list, model: str = "gpt-3.5-turbo") -> str:
    try:
        # ✅ используем acreate
        response: ChatCompletion = await client.chat.completions.acreate(
            model=model,
            messages=messages
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[GPT Error] {e}")
        return "⚠️ Ошибка при обращении к GPT."
