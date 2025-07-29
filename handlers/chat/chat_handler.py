from telegram import Update
from telegram.ext import ContextTypes
from components.gpt_client import ask_gpt
from components.voice import synthesize_voice
from components.mode import MODE_SWITCH_MESSAGES
from state.session import user_sessions
import os

MAX_HISTORY_LENGTH = 40

STYLE_MAP = {
    "casual": (
        "Be relaxed, humorous, and use casual expressions. Use emojis, memes, and playful phrases. "
        "Sound like a cheerful buddy. Stay ultra-positive and fun, like a witty friend."
    ),
    "business": (
        "Respond with a professional, respectful, and slightly formal tone. Avoid emojis unless absolutely necessary. "
        "Maintain a friendly and engaging presence — like a smart colleague or helpful mentor. "
        "Do not sound robotic or overly stiff. Keep it human and clear."
    )
}

LANGUAGE_CODES = {
    "en": "en-US",
    "fr": "fr-FR",
    "de": "de-DE",
    "es": "es-ES",
    "ru": "ru-RU"
}

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
    style = session.get("style", "casual").lower()
    mode = session["mode"]
    history = session["history"]

    voice_triggers = ["скажи голосом", "включи голос", "озвучь", "произнеси", "скажи это", "как это звучит", "давай голосом"]
    text_triggers = ["вернись к тексту", "хочу текст", "пиши", "текстом", "не надо голосом"]
    lower_input = user_input.lower()

    if any(trigger in lower_input for trigger in voice_triggers):
        session["mode"] = "voice"
        await update.message.reply_text(MODE_SWITCH_MESSAGES["voice"].get(interface_lang, "Voice mode on."))
        await update.message.reply_text("Только скажи, что хочешь вернуться в текстовый режим — и я перестану доставать тебя голосовыми 😁")
        return

    elif any(trigger in lower_input for trigger in text_triggers):
        session["mode"] = "text"
        await update.message.reply_text(MODE_SWITCH_MESSAGES["text"].get(interface_lang, "Text mode on."))
        return

    rules = get_rules_by_level(level, interface_lang)
    persona = get_greeting_name(interface_lang)
    style_instructions = STYLE_MAP.get(style, STYLE_MAP["casual"])

    system_prompt = (
        f"You are {persona}, a friendly assistant helping the user learn {target_lang.upper()}.\n"
        f"Always respond ONLY in {target_lang.upper()}.\n"
        f"User level: {level.upper()}. Style: {style}.\n"
        f"{style_instructions}\n"
        f"{rules}"
    )

    if mode == "voice":
        system_prompt += (
            "\nSpeak naturally, as if talking aloud. "
            "Avoid emojis and formatting. Express tone with words, not symbols."
        )
    else:
        system_prompt += "\nWritten responses can include emojis and formatting depending on style."

    history.append({"role": "user", "content": user_input})
    if len(history) > MAX_HISTORY_LENGTH:
        history.pop(0)

    messages = [{"role": "system", "content": system_prompt}] + history

    try:
        response_text = ask_gpt(messages)
        history.append({"role": "assistant", "content": response_text})

        if mode == "voice":
            lang_code = LANGUAGE_CODES.get(target_lang, target_lang)
            audio_path = synthesize_voice(response_text, lang=lang_code, level=level)
            with open(audio_path, "rb") as audio:
                await update.message.reply_voice(voice=audio)
            os.remove(audio_path)
        else:
            await update.message.reply_text(response_text)

    except Exception as e:
        await update.message.reply_text("⚠️ Ошибка при обращении к GPT.")
        print(f"GPT error: {e}")
