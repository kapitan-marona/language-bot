# handlers/chat/chat_handler.py

from telegram import Update
from telegram.ext import ContextTypes
from config.config import OPENAI_API_KEY
import openai

openai.api_key = OPENAI_API_KEY

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text

    # GPT system prompt
    system_prompt = "You are a helpful language learning assistant. Wrap important words in tildes (~like this~)."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",  # можно заменить на gpt-3.5-turbo
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        )

        reply = response.choices[0].message.content
        await update.message.reply_text(reply)

    except Exception as e:
        await update.message.reply_text("⚠️ Ошибка при обращении к GPT")
        print(f"[ERROR] GPT: {e}")
