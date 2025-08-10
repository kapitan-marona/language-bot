import os
import time
import random
import re
import tempfile
from io import BytesIO
import openai
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from config.config import ADMINS

from components.gpt_client import ask_gpt, transcribe_audio, synthesize_tts
from components.voice import synthesize_voice  # (fallback)
# Prefer OpenAI TTS:
from components.gpt_client import synthesize_tts
from components.mode import MODE_SWITCH_MESSAGES, get_mode_keyboard
from state.session import user_sessions
from handlers.chat.prompt_templates import get_system_prompt, START_MESSAGE, MATT_INTRO, INTRO_QUESTIONS
from components.triggers import CREATOR_TRIGGERS, MODE_TRIGGERS
from components.triggers import is_strict_mode_trigger, is_strict_say_once_trigger  # <-- добавлено

logger = logging.getLogger(__name__)

MAX_HISTORY_LENGTH = 40
RATE_LIMIT_SECONDS = 1.5

LANGUAGE_CODES = {
    "en": "en-US",
    "fr": "fr-FR",
    "de": "de-DE",
    "es": "es-ES",
    "ru": "ru-RU",
    "sv": "sv-SE",
    "fi": "fi-FI"
}

def get_greeting_name(lang: str) -> str:
    return "Matt" if lang == "en" else "Мэтт"

def _sanitize_user_text(text: str, max_len: int = 2000) -> str:
    text = (text or "").strip()
    if len(text) > max_len:
        text = text[:max_len]
    return text

# --- Главный message handler ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})

    # === ВСТАВКА: если ждём промокод, отдаём в обработчик промокода и выходим ===
    try:
        stage = session.get("onboarding_stage")
    except Exception:
        stage = None

    if stage == "awaiting_promo":
        from components.onboarding import promo_code_message
        return await promo_code_message(update, context)
    # === КОНЕЦ ВСТАВКИ ===

    # --- RATE LIMITING ---
    now = time.time()
    last_time = session.get("last_message_time", 0)
    if now - last_time < RATE_LIMIT_SECONDS:
        await context.bot.send_message(chat_id=chat_id, text="⏳ Погоди, думаю 🙂")
        return
    session["last_message_time"] = now

    try:
        # --- session defaults ---
        session.setdefault("interface_lang", "en")
        session.setdefault("target_lang", "en")
        session.setdefault("level", "A2")
        session.setdefault("mode", "text")
        session.setdefault("style", "casual")

        # --- Получаем все значения из сессии для универсального доступа ---
        interface_lang = session["interface_lang"]
        target_lang = session["target_lang"]
        level = session["level"]
        mode = session["mode"]
        style = session["style"]

        # === ОБРАБОТКА ВХОДЯЩЕГО СООБЩЕНИЯ: текст или голос ===
        if update.message.voice:
            # --- Распознавание голоса через Whisper ---
            voice_file = await context.bot.get_file(update.message.voice.file_id)
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tf:
                await voice_file.download_to_drive(tf.name)
                audio_path = tf.name

            try:
                with open(audio_path, "rb") as f:
                    transcript = openai.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                        response_format="text"
                    )
                user_input = (transcript or "").strip()
                logger.info("Whisper recognized text: %r", user_input)
            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text="❗️Ошибка распознавания голоса. Попробуй ещё раз.")
                logger.exception("[Whisper Error]")
                user_input = ""
            finally:
                try:
                    os.remove(audio_path)
                except Exception as e_rm:
                    logger.warning("Failed to remove temp audio: %s", e_rm)
        else:
            # --- Обычный текст ---
            user_input = update.message.text or ""

        # Санитизация текста от слишком длинных сообщений
        user_input = _sanitize_user_text(user_input, max_len=2000)

        # --- Если пустой текст — сообщаем пользователю и выходим ---
        if not user_input:
            await context.bot.send_message(chat_id=chat_id, text="❗️Похоже, сообщение не распознано. Скажи что-нибудь ещё 🙂")
            return

        # === Разовая озвучка без смены режима ===
        # (если пользователь написал "озвучь"/"voice it" и т.п.)
        if is_strict_say_once_trigger(user_input, interface_lang):
            last_text = session.get("last_assistant_text")
            if not last_text:
                if interface_lang == "ru":
                    await update.message.reply_text("Пока мне нечего озвучить. Сначала дождись моего ответа, а потом напиши «озвучь».")
                else:
                    await update.message.reply_text("I have nothing to voice yet. First wait for my reply, then say “voice it”.")
                return

            try:
                audio_bytes = await synthesize_tts(last_text, voice="alloy")
                if audio_bytes:
                    await context.bot.send_audio(chat_id=chat_id, audio=BytesIO(audio_bytes), filename="reply.mp3", title="Bot reply")
                else:
                    # Fallback to old pipeline
                    voice_path = synthesize_voice(last_text, LANGUAGE_CODES.get(target_lang, "en-US"), level)
                    if voice_path:
                        with open(voice_path, "rb") as vf:
                            await context.bot.send_voice(chat_id=chat_id, voice=vf)
                    else:
                        if interface_lang == "ru":
                            await update.message.reply_text("Не получилось озвучить. Попробуй ещё раз чуть позже.")
                        else:
                            await update.message.reply_text("Couldn't generate voice right now. Try again later.")
                return  # ВАЖНО: режим не меняем, продолжаем обычный диалог дальше

        # === Универсальная обработка триггеров ===
        # Строгое переключение режима: команда должна совпасть целиком
        if is_strict_mode_trigger(user_input, "voice"):
            session["mode"] = "voice"
            msg = MODE_SWITCH_MESSAGES["voice"].get(interface_lang, MODE_SWITCH_MESSAGES["voice"]["en"])
            await update.message.reply_text(msg, reply_markup=get_mode_keyboard("voice", interface_lang))
            return

        if is_strict_mode_trigger(user_input, "text"):
            session["mode"] = "text"
            msg = MODE_SWITCH_MESSAGES["text"].get(interface_lang, MODE_SWITCH_MESSAGES["text"]["en"])
            await update.message.reply_text(msg, reply_markup=get_mode_keyboard("text", interface_lang))
            return

        # Мягкая подсказка: если фраза "похожа", но не точная команда — не отправляем в GPT
        user_text_norm = user_input.lower()
        if any(phrase in user_text_norm for phrase in MODE_TRIGGERS["voice"]):
            if interface_lang == "ru":
                await update.message.reply_text("Если хочешь перейти в голосовой режим — просто напиши **голос** 😉", parse_mode="Markdown")
            else:
                await update.message.reply_text("To switch to voice mode, just type **voice** 😉", parse_mode="Markdown")
            return

        if any(phrase in user_text_norm for phrase in MODE_TRIGGERS["text"]):
            if interface_lang == "ru":
                await update.message.reply_text("Чтобы перейти в текстовый режим, напиши **текст** 🙂", parse_mode="Markdown")
            else:
                await update.message.reply_text("To switch to text mode, type **text** 🙂", parse_mode="Markdown")
            return

        # --- Обработка запроса про создателя/разработчика ---
        found_trigger = False
        norm_for_creator = re.sub(r'[^\w\s]', '', user_input.lower())
        for trig in CREATOR_TRIGGERS.get(interface_lang, CREATOR_TRIGGERS["en"]):
            if trig in norm_for_creator:
                found_trigger = True
                break

        if found_trigger:
            if interface_lang == "ru":
                reply_text = "🐾 Мой создатель — @marrona! Для обратной связи и предложений к сотрудничеству обращайся прямо к ней. 🌷"
            else:
                reply_text = "🐾 My creator is @marrona! For feedback or collaboration offers, feel free to contact her directly. 🌷"
            await update.message.reply_text(reply_text)
            return

        # --- Переписка с GPT ---
        history = session.setdefault("history", [])

        # --- Формируем system prompt ---
        system_prompt = get_system_prompt(style, level, interface_lang, target_lang, mode)
        prompt = [{"role": "system", "content": system_prompt}]
        for msg in history:
            prompt.append(msg)
        prompt.append({"role": "user", "content": user_input})

        assistant_reply = await ask_gpt(prompt, "gpt-4o")

        # --- История переписки ---
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": assistant_reply})
        if len(history) > MAX_HISTORY_LENGTH:
            history.pop(0)

        # --- Ответ: текст или голос ---
        if mode == "voice":
            try:
                tts_bytes = await synthesize_tts(assistant_reply, voice="alloy")
                if tts_bytes:
                    await context.bot.send_audio(chat_id=chat_id, audio=BytesIO(tts_bytes), filename="reply.mp3", title="Bot reply")
                    if level in ["A0", "A1", "A2"]:
                        await context.bot.send_message(chat_id=chat_id, text=assistant_reply)
                else:
                    # Fallback to legacy voice path
                    voice_path = synthesize_voice(assistant_reply, LANGUAGE_CODES.get(target_lang, "en-US"), level)
                    with open(voice_path, "rb") as vf:
                        await context.bot.send_voice(chat_id=chat_id, voice=vf)
            except Exception:
                logger.exception("[Ошибка отправки голоса]")
                await context.bot.send_message(chat_id=chat_id, text="⚠️ Не удалось отправить голосовое сообщение. Вот текст:\n" + assistant_reply)
            finally:
                session["last_assistant_text"] = assistant_reply  # <-- фиксируем последний ответ ассистента
        else:
            await update.message.reply_text(assistant_reply)
            session["last_assistant_text"] = assistant_reply  # <-- фиксируем последний ответ ассистента

    except Exception:
        logger.exception("[ОШИБКА в handle_message]")
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Что-то пошло не так! Попробуй ещё раз или перезапусти бота командой /start.")
