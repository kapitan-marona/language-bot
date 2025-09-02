import os
import time
import random
import re
import tempfile
import logging
from html import unescape  # NEW: для безопасного plain-дубля
from telegram import Update
from telegram.ext import ContextTypes

from config.config import ADMINS, OPENAI_API_KEY
from openai import OpenAI  # новый клиент для ASR

from components.gpt_client import ask_gpt
from components.voice import synthesize_voice
from components.mode import MODE_SWITCH_MESSAGES, get_mode_keyboard
from state.session import user_sessions
from handlers.chat.prompt_templates import get_system_prompt
from components.triggers import CREATOR_TRIGGERS, MODE_TRIGGERS
from components.triggers import is_strict_mode_trigger, is_strict_say_once_trigger
from components.code_switch import rewrite_mixed_input  # ← NEW

logger = logging.getLogger(__name__)

oai_asr = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

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

# ====================== СТИКЕРЫ + МУЛЬТИЯЗЫЧНЫЕ ТРИГГЕРЫ ======================

# --- Стикеры (реальные file_id) ---
STICKERS = {
    "hello": ["CAACAgIAAxkBAAItV2i269d_71pHUu5Rm9f62vsCW0TrAAJJkAAC96S4SXJs5Yp4uIyENgQ"],
    "fire":  ["CAACAgIAAxkBAAItWWi26-vSBaRPbX6a2imIoWq4Jo0pAALhfwAC6gm5SSTLD1va-EfRNgQ"],
    "sorry": ["CAACAgIAAxkBAAItWGi26-jb1_zQAAE1IyLH1XfqWH5aZQAC3oAAAt7vuUlXHMvWZt7gQDYE"],
}

async def maybe_send_sticker(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, key: str, chance: float = 0.35):
    """Иногда отправляет стикер по ключу. Ничего не делает, если ключ не найден."""
    try:
        if key not in STICKERS:
            return
        if random.random() < chance:
            await ctx.bot.send_sticker(chat_id=chat_id, sticker=random.choice(STICKERS[key]))
    except Exception:
        # стикер — «приятная добавка», падать нет смысла
        pass

# --- Лёгкий детектор интентов (мультиязычный, без зависимостей) ---
_GREET_EMOJI = {"👋", "🤝"}
_COMPLIMENT_EMOJI = {"🔥", "💯", "👏", "🌟", "👍", "❤️", "💖", "✨"}

# Стемы/слова по поддерживаемым языкам (коротко и общеупотребимо)
_GREET_WORDS = {
    # en
    "hi", "hello", "hey",
    # ru
    "привет", "здравствуй", "здорово", "хай", "хелло",
    # fr
    "bonjour", "salut",
    # es
    "hola", "buenas",
    # de
    "hallo", "servus", "moin",
    # sv
    "hej", "hejsan", "tjena",
    # fi
    "hei", "moi", "terve",
}

_COMPLIMENT_STEMS = {
    # en
    "great", "awesome", "amazing", "love it", "nice", "cool",
    # ru
    "класс", "супер", "топ", "круто", "молодец", "огонь",
    # fr
    "super", "génial", "genial", "top", "formid",
    # es
    "genial", "increíble", "increible", "super", "top", "bravo",
    # de
    "super", "toll", "klasse", "mega", "geil",
    # sv
    "super", "grym", "toppen", "snyggt", "bra jobbat",
    # fi
    "mahtava", "huikea", "upea", "super", "hieno",
}

_SORRY_STEMS = {
    # en
    "sorry", "apolog", "my bad", "wrong", "mistake", "incorrect",
    "you’re wrong", "you are wrong",
    # ru
    "прости", "извин", "ошиб", "не так", "неправил", "ты ошиб",
    # fr
    "désolé", "desole", "pardon", "erreur", "faux",
    # es
    "perdón", "perdon", "lo siento", "error", "equivoc",
    # de
    "sorry", "entschuldig", "fehler", "falsch",
    # sv
    "förlåt", "forlat", "fel",
    # fi
    "anteeksi", "virhe", "väärin", "vaarin",
}

def _norm_msg_keep_emoji(s: str) -> str:
    s = (s or "").lower()
    # сохраняем эмодзи (диапазон U+1F300–U+1FAFF), оставляем латиницу и кириллицу
    s = re.sub(r"[^\w\s\u0400-\u04FF\u00C0-\u024F\u1F300-\u1FAFF]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def is_greeting(raw: str) -> bool:
    if not raw:
        return False
    if any(e in raw for e in _GREET_EMOJI):
        return True
    msg = _norm_msg_keep_emoji(raw)
    words = set(msg.split())
    return any(w in words for w in _GREET_WORDS)

def is_compliment(raw: str) -> bool:
    if not raw:
        return False
    if any(e in raw for e in _COMPLIMENT_EMOJI):
        return True
    msg = _norm_msg_keep_emoji(raw)
    return any(kw in msg for kw in _COMPLIMENT_STEMS)

def is_correction(raw: str) -> bool:
    if not raw:
        return False
    msg = _norm_msg_keep_emoji(raw)
    return any(kw in msg for kw in _SORRY_STEMS)

# ====================== /СТИКЕРЫ ======================


def get_greeting_name(lang: str) -> str:
    return "Matt" if lang == "en" else "Мэтт"


def _sanitize_user_text(text: str, max_len: int = 2000) -> str:
    text = (text or "").strip()
    if len(text) > max_len:
        text = text[:max_len]
    return text


def _strip_html(s: str) -> str:
    """Удаляем HTML-теги и декодируем сущности для безопасного plain-текста."""
    return re.sub(r"<[^>\n]+>", "", unescape(s or ""))


async def _send_voice_or_audio(context: ContextTypes.DEFAULT_TYPE, chat_id: int, file_path: str):
    """
    Если .ogg — шлём как voice, иначе (.mp3) — как audio.
    """
    if file_path.lower().endswith(".ogg"):
        with open(file_path, "rb") as vf:
            await context.bot.send_voice(chat_id=chat_id, voice=vf)
    else:
        with open(file_path, "rb") as af:
            await context.bot.send_audio(chat_id=chat_id, audio=af)


# --- Главный message handler ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})

    # === Если ждём промокод — делегируем и выходим ===
    try:
        stage = session.get("onboarding_stage")
    except Exception:
        stage = None
    if stage == "awaiting_promo":
        from components.onboarding import promo_code_message
        return await promo_code_message(update, context)

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

        # --- Достаём значения из сессии ---
        interface_lang = session["interface_lang"]
        target_lang = session["target_lang"]
        level = session["level"]
        mode = session["mode"]
        style = session["style"]

        # === Вход: голос или текст ===
        if update.message.voice:
            if not oai_asr:
                await context.bot.send_message(chat_id=chat_id, text="❗️ASR недоступен. Попробуй ещё раз позже.")
                return

            voice_file = await context.bot.get_file(update.message.voice.file_id)
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tf:
                await voice_file.download_to_drive(tf.name)
                audio_path = tf.name
            try:
                with open(audio_path, "rb") as f:
                    tr = oai_asr.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                    )
                user_input = (getattr(tr, "text", "") or "").strip()
                logger.info("Whisper recognized text: %r", user_input)
            except Exception:
                await context.bot.send_message(chat_id=chat_id, text="❗️Ошибка распознавания голоса. Попробуй ещё раз.")
                logger.exception("[Whisper Error]")
                user_input = ""
            finally:
                try:
                    os.remove(audio_path)
                except Exception as e_rm:
                    logger.warning("Failed to remove temp audio: %s", e_rm)
        else:
            user_input = update.message.text or ""

        user_input = _sanitize_user_text(user_input, max_len=2000)
        if not user_input:
            await context.bot.send_message(chat_id=chat_id, text="❗️Похоже, сообщение не распознано. Скажи что-нибудь ещё 🙂")
            return

        # === Переключения режимов (только явные короткие команды) ===
        def _norm(s: str) -> str:
            s = re.sub(r"[^\w\s]", " ", (s or "").lower())
            s = re.sub(r"\s+", " ", s).strip()
            return s

        msg_norm = _norm(user_input)

        VOICE_STRICT = {
            "голос", "в голос", "в голосовой режим",
            "voice", "voice mode"
        }
        TEXT_STRICT = {
            "текст", "в текст", "в текстовый режим",
            "text", "text mode"
        }

        # --- Сначала проверим переключения: при них НИКАКИХ стикеров ---
        if msg_norm in VOICE_STRICT:
            if session["mode"] != "voice":
                session["mode"] = "voice"
                msg = MODE_SWITCH_MESSAGES["voice"].get(interface_lang, MODE_SWITCH_MESSAGES["voice"]["en"])
                await update.message.reply_text(msg, reply_markup=get_mode_keyboard("voice", interface_lang))
            return

        if msg_norm in TEXT_STRICT:
            if session["mode"] != "text":
                session["mode"] = "text"
                msg = MODE_SWITCH_MESSAGES["text"].get(interface_lang, MODE_SWITCH_MESSAGES["text"]["en"])
                await update.message.reply_text(msg, reply_markup=get_mode_keyboard("text", interface_lang))
            return

        # --- Стикеры по интентам (мультиязычно). Здесь уже можно.
        msg_raw = user_input or ""
        if is_greeting(msg_raw):
            await maybe_send_sticker(context, chat_id, "hello", chance=0.4)
        if is_compliment(msg_raw):
            await maybe_send_sticker(context, chat_id, "fire", chance=0.35)
        if is_correction(msg_raw):
            # ВАЖНО: стикер – только «иногда». Текстовые извинения по промпту — не трогаем.
            await maybe_send_sticker(context, chat_id, "sorry", chance=0.35)

        # --- Создатель ---
        found_trigger = False
        norm_for_creator = re.sub(r"[^\w\s]", "", user_input.lower())
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

        # --- История + системный промпт ---
        history = session.setdefault("history", [])
        system_prompt = get_system_prompt(style, level, interface_lang, target_lang, mode)
        prompt = [{"role": "system", "content": system_prompt}]
        prompt.extend(history)

        # --- Лёгкая починка смешанной фразы ---
        clean_user_input, preface_html = await rewrite_mixed_input(
            user_input, interface_lang, target_lang
        )
        prompt.append({"role": "user", "content": clean_user_input})

        assistant_reply = await ask_gpt(prompt, "gpt-4o")

        # --- История ---
        history.append({"role": "user", "content": clean_user_input})
        history.append({"role": "assistant", "content": assistant_reply})
        if len(history) > MAX_HISTORY_LENGTH:
            history.pop(0)

        # --- Отправка ответа ---
        final_reply_text = f"{preface_html}\n\n{assistant_reply}" if preface_html else assistant_reply

        if mode == "voice":
            voice_path = synthesize_voice(assistant_reply, LANGUAGE_CODES.get(target_lang, "en-US"), level)
            try:
                if voice_path:
                    await _send_voice_or_audio(context, chat_id, voice_path)
                else:
                    raise RuntimeError("No TTS data")
            except Exception:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="⚠️ Не удалось отправить голос. Вот текст:\n" + _strip_html(final_reply_text),
                )
            if level in ["A0", "A1", "A2"]:
                try:
                    await context.bot.send_message(chat_id=chat_id, text=_strip_html(final_reply_text))
                except Exception:
                    pass
            session["last_assistant_text"] = assistant_reply
        else:
            await update.message.reply_text(final_reply_text, parse_mode="HTML")
            session["last_assistant_text"] = assistant_reply

    except Exception:
        logger.exception("[ОШИБКА в handle_message]")
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Что-то пошло не так! Попробуй ещё раз или перезапусти бота командой /start.")
