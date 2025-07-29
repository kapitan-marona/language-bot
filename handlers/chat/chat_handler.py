# handlers/chat/chat_handler.py
from telegram import Update
from telegram.ext import ContextTypes
from components.gpt_client import ask_gpt
from components.voice import synthesize_voice
from components.mode import MODE_SWITCH_MESSAGES
from state.session import user_sessions
import os

MAX_HISTORY_LENGTH = 40

def get_rules_by_level(level: str, interface_lang: str) -> str:
    rules = {
        "A0": {
            "en": "Use the simplest grammar and translate everything you say to English.",
            "ru": "Используй самую простую грамматику и переводи всё, что говоришь, на русский.",
        },
        "A1": {
            "en": "Use simple grammar. Translate only if asked.",
            "ru": "Используй простую грамматику. Переводи только по просьбе.",
        },
        "B1": {
            "en": "Use more advanced grammar. Only translate when requested.",
            "ru": "Используй более сложную грамматику. Переводи только по запросу.",
        },
        "C1": {
            "en": "Communicate as with a native speaker. No translation unless asked.",
            "ru": "Общайся как с нейтивом. Не переводи без просьбы.",
        },
    }
    for key in rules:
        if level.upper().startswith(key):
            return rules[key].get(interface_lang, rules[key]["en"])
    return rules["B1"][interface_lang]  # fallback


def get_greeting_name(lang: str) -> str:
    return "Matt" if lang == "en" else "Мэтт"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_input = update.message.text

    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}

    session = user_sessions[chat_id]
    session.setdefault("interface_lang", "en")
    session.setdefault("target_lang", "en")
    session.setdefault("level", "A1")
    session.setdefault("style", "casual")
    session.setdefault("mode", "text")
    session.setdefault("history", [])

    interface_lang = session["interface_lang"]
    target_lang = session["target_lang"]
    level = session["level"]
    style = session["style"]
    mode = session["mode"]
    history = session["history"]

    rules = get_rules_by_level(level, interface_lang)
    persona = get_greeting_name(interface_lang)

    tone = {
        "casual": "Speak like a funny, friendly mate with emojis and slang.",
        "buisness": "Speak formally, politely, and respectfully. Minimal emojis.",
    }[style]

    system_prompt = (
        f"You are {persona}, a friendly assistant helping learn {target_lang}. "
        f"User level: {level}. Style: {style}.\n"
        f"{tone}\n"
        f"{rules}"
    )

    # Обновить историю
    history.append({"role": "user", "content": user_input})
    if len(history) > MAX_HISTORY_LENGTH:
        history.pop(0)

    messages = [{"role": "system", "content": system_prompt}] + history

    try:
        response_text = ask_gpt(messages)
        history.append({"role": "assistant", "content": response_text})

        if mode == "voice":
            audio_path = synthesize_voice(response_text, lang=target_lang, level=level)
            with open(audio_path, "rb") as audio:
                await update.message.reply_voice(voice=audio)
            os.remove(audio_path)
        else:
            await update.message.reply_text(response_text)

    except Exception as e:
        await update.message.reply_text("⚠️ Ошибка при обращении к GPT.")
        print(f"GPT error: {e}")
