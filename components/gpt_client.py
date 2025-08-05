import openai
import os

# Получаем API-ключ из переменных окружения, это безопаснее
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Основная функция для работы с GPT
async def ask_gpt(messages, model="gpt-3.5-turbo"):
    """
    Делает асинхронный запрос к OpenAI GPT API.

    :param messages: List[Dict], формат истории сообщений для ChatCompletion.
    :param model: str, модель GPT (по умолчанию gpt-3.5-turbo, для экономии; gpt-4o — если хочешь лучше).
    :return: str, сгенерированный ответ.
    """
    try:
        response = await openai.ChatCompletion.acreate(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=700,
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        print(f"[GPT ERROR]: {e}")
        return "⚠️ Ошибка генерации ответа. Попробуйте еще раз!"

