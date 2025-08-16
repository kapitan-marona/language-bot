from telegram import Update
from telegram.ext import ContextTypes
from config import client
from handlers.voice import speak_and_reply
from handlers.keyboards import voice_mode_button, text_mode_button, learn_lang_markup
from .prompts import generate_system_prompt, build_correction_instruction
from .text_utils import extract_marked_words, is_russian
import random


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text_override: str = None):
    user_text = user_text_override or (update.message.text if update.message else None)

    if not user_text:
        await update.message.reply_text("Не удалось обработать сообщение.")
        return

    user_text = user_text.strip()
    normalized_text = user_text.lower()
l

    # 🧩 Prompt + correction rules
    native_lang = context.user_data.get("language", "English")
    learn_lang = context.user_data.get("learn_lang", "English")
    style = context.user_data.get("style", "casual")
    voice_mode = context.user_data.get("voice_mode", False)

    correction_instruction = build_correction_instruction(native_lang, learn_lang, level)
    system_prompt = generate_system_prompt(
        interface_lang=native_lang,
        level=level,
        style=style,
        learn_lang=learn_lang,
        voice_mode=voice_mode
    ) + " " + correction_instruction

    # 💬 Chat history
    chat_history = context.user_data.setdefault("chat_history", [])
    chat_history.append({"role": "user", "content": user_text})
    context.user_data["chat_history"] = chat_history[-40:]

    messages = [{"role": "system", "content": system_prompt}] + context.user_data["chat_history"]

    try:
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7
        )
        answer = completion.choices[0].message.content

        # 📚 Dictionary update
        dictionary = context.user_data.setdefault("dictionary", set())
        for word in extract_marked_words(answer):
            cleaned_word = word.strip()
            if not is_russian(cleaned_word):
                dictionary.add(cleaned_word)

        # 💬 Save answer to history
        context.user_data["chat_history"].append({"role": "assistant", "content": answer})
        context.user_data["chat_history"] = context.user_data["chat_history"][-40:]

        # 🗣 Voice or text response
        if context.user_data.get("voice_mode"):
            await speak_and_reply(answer, update, context)
            await update.message.reply_text(" ", reply_markup=text_mode_button)
        else:
            await update.message.reply_text(answer, reply_markup=voice_mode_button)


    except Exception:
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
