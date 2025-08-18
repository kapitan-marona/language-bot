from __future__ import annotations
import os
import time
import random
import re
import tempfile
import logging
import asyncio
import io
from inspect import iscoroutinefunction
from telegram import Update
from telegram.ext import ContextTypes
from config.config import ADMINS

from openai import AsyncOpenAI  # async-клиент OpenAI
openai_client = AsyncOpenAI()

from components.gpt_client import ask_gpt
from components.voice import synthesize_voice as _synthesize_voice
from components.mode import MODE_SWITCH_MESSAGES, get_mode_keyboard
from state.session import user_sessions
from handlers.chat.prompt_templates import (
    get_system_prompt,
    START_MESSAGE,
    MATT_INTRO,
    INTRO_QUESTIONS,
    INTRO_QUESTIONS_EASY,  # <- простые вопросы для A0–A2
)
from components.triggers import CREATOR_TRIGGERS, MODE_TRIGGERS
from components.triggers import is_strict_mode_trigger, is_strict_say_once_trigger

logger = logging.getLogger("english-bot")

MAX_HISTORY_LENGTH = 40
RATE_LIMIT_SECONDS = 1.5

LANGUAGE_CODES = {
    "en": "en-US",
    "fr": "fr-FR",
    "de": "de-DE",
    "es": "es-ES",
    "ru": "ru-RU",
    "sv": "sv-SE",
    "fi": "fi-FI",
}

def _sanitize_user_text(text: str, max_len: int = 2000) -> str:
    text = (text or "").strip()
    if len(text) > max_len:
        text = text[:max_len]
    return text

# --- нормализация текста и триггеров «про автора» ---
def _norm_text(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s

_ALL_CREATOR_TRIGS_NORM = tuple({
    _norm_text(t) for lst in CREATOR_TRIGGERS.values() for t in lst
})

# Единая async-обёртка над TTS (передаём и style, и level!)
async def synthesize_voice_async(text: str, lang_code: str, style: str, level: str) -> str | None:
    if iscoroutinefunction(_synthesize_voice):
        # сигнатура synthesize_voice(text, language_code, style="casual", level="A2")
        return await _synthesize_voice(text, lang_code, style=style, level=level)
    # если вдруг синхронная — в тред-пуле
    return await asyncio.to_thread(_synthesize_voice, text, lang_code, style, level)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else None
    session = user_sessions.setdefault(chat_id, {})

    # Диагностика входа
    try:
        txt = (getattr(update.message, "text", "") or "")[:80]
        stage = session.get("onboarding_stage")
        logger.info("[chat] enter user=%s chat=%s stage=%r text=%r", user_id, chat_id, stage, txt)
    except Exception:
        pass

    # Если ждём промокод — отдаём обработчику промокода и выходим
    try:
        stage = session.get("onboarding_stage")
    except Exception:
        stage = None
    if stage == "awaiting_promo":
        from components.onboarding import promo_code_message
        return await promo_code_message(update, context)

    # Rate limiting
    now = time.time()
    last_time = session.get("last_message_time", 0.0)
    if now - last_time < RATE_LIMIT_SECONDS:
        await context.bot.send_message(chat_id=chat_id, text="⏳ Погоди, думаю 🙂")
        return
    session["last_message_time"] = now

    try:
        # Defaults в сессии
        session.setdefault("interface_lang", "en")
        session.setdefault("target_lang", "en")
        session.setdefault("level", "A2")
        session.setdefault("mode", "text")
        session.setdefault("style", "casual")

        interface_lang = session["interface_lang"]
        target_lang = session["target_lang"]
        level = session["level"]
        mode = session["mode"]
        style = session["style"]

        # Текст или голос
        if update.message and update.message.voice:
            voice_file = await context.bot.get_file(update.message.voice.file_id)
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tf:
                await voice_file.download_to_drive(tf.name)
                audio_path = tf.name

            try:
                f = await asyncio.to_thread(open, audio_path, "rb")
                try:
                    transcript = await openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                        response_format="text",
                    )
                finally:
                    await asyncio.to_thread(f.close)
                user_input = (transcript or "").strip()
                logger.info("Whisper recognized text: %r", user_input)
            except Exception:
                await context.bot.send_message(chat_id=chat_id, text="❗️Ошибка распознавания голоса. Попробуй ещё раз.")
                logger.exception("[Whisper Error]")
                user_input = ""
            finally:
                try:
                    await asyncio.to_thread(os.remove, audio_path)
                except Exception as e_rm:
                    logger.warning("Failed to remove temp audio: %s", e_rm)
        else:
            user_input = (update.message.text if update.message else "") or ""

        user_input = _sanitize_user_text(user_input, max_len=2000)
        if not user_input:
            await context.bot.send_message(chat_id=chat_id, text="❗️Похоже, сообщение не распознано. Скажи что-нибудь ещё 🙂")
            return

        # Разовая озвучка (без смены режима)
        if is_strict_say_once_trigger(user_input, interface_lang):
            last_text = session.get("last_assistant_text")
            if not last_text:
                if interface_lang == "ru":
                    await update.message.reply_text("Пока мне нечего озвучить. Сначала дождись моего ответа, а потом напиши «озвучь».")
                else:
                    await update.message.reply_text("I have nothing to voice yet. First wait for my reply, then say “voice it”.")
                return
            try:
                voice_path = await synthesize_voice_async(
                    last_text,
                    LANGUAGE_CODES.get(target_lang, "en-US"),
                    style,          # <- стиль
                    level,          # <- уровень
                )
                if voice_path:
                    data = await asyncio.to_thread(lambda: open(voice_path, "rb").read())
                    bio = io.BytesIO(data)
                    bio.name = "voice.ogg"
                    await context.bot.send_voice(chat_id=chat_id, voice=bio)
                else:
                    if interface_lang == "ru":
                        await update.message.reply_text("Не получилось озвучить. Попробуй ещё раз чуть позже.")
                    else:
                        await update.message.reply_text("Couldn’t generate audio. Please try again later.")
            except Exception:
                logger.exception("[One-shot TTS error]")
                if interface_lang == "ru":
                    await update.message.reply_text("Произошла ошибка при озвучке. Попробуем позже.")
                else:
                    await update.message.reply_text("An error occurred while generating audio. Let’s try later.")
            finally:
                return

        # Переключатели режимов (строгие команды)
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

        # Мягкие подсказки
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

        # Вопрос про создателя (нормализуем и вход, и триггеры; проверяем все языки)
        text_norm = _norm_text(user_input)
        found_trigger = any(t in text_norm for t in _ALL_CREATOR_TRIGS_NORM)
        if found_trigger:
            if interface_lang == "ru":
                reply_text = "🐾 Мой создатель — @marrona! Для обратной связи и предложений к сотрудничеству обращайся прямо к ней. 🌷"
            else:
                reply_text = "🐾 My creator is @marrona! For feedback or collaboration offers, feel free to contact her directly. 🌷"
            await update.message.reply_text(reply_text)
            return

        # Диалог с GPT
        history = session.setdefault("history", [])

        system_prompt = get_system_prompt(style, level, interface_lang, target_lang, mode)
        prompt = [{"role": "system", "content": system_prompt}]
        for msg in history:
            prompt.append(msg)
        prompt.append({"role": "user", "content": user_input})

        assistant_reply = await ask_gpt(prompt, "gpt-4o")

        # История
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": assistant_reply})
        if len(history) > MAX_HISTORY_LENGTH:
            history.pop(0)

        # Ответ: голос/текст
        if mode == "voice":
            voice_path = await synthesize_voice_async(
                assistant_reply,
                LANGUAGE_CODES.get(target_lang, "en-US"),
                style,      # <- стиль
                level,      # <- уровень
            )
            try:
                if voice_path:
                    data = await asyncio.to_thread(lambda: open(voice_path, "rb").read())
                    bio = io.BytesIO(data)
                    bio.name = "voice.ogg"
                    await context.bot.send_voice(chat_id=chat_id, voice=bio)
                if level == "A0":
                    await context.bot.send_message(chat_id=chat_id, text=f"{assistant_reply}\n\n 💌")
                elif level in ["A1", "A2"]:
                    await context.bot.send_message(chat_id=chat_id, text=assistant_reply)
            except Exception:
                logger.exception("[Ошибка отправки голоса]")
                await context.bot.send_message(chat_id=chat_id, text="⚠️ Не удалось отправить голосовое сообщение. Вот текст:\n" + assistant_reply)
            finally:
                session["last_assistant_text"] = assistant_reply
        else:
            await update.message.reply_text(assistant_reply)
            session["last_assistant_text"] = assistant_reply

    except Exception:
        logger.exception("[ОШИБКА в handle_message]")
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Что-то пошло не так! Попробуй ещё раз или перезапусти бота командой /start.")
