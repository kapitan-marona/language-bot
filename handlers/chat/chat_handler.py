import os
import time
import random
import re
import tempfile
import logging
from html import unescape
from telegram import Update
from telegram.ext import ContextTypes

from config.config import OPENAI_API_KEY
from openai import OpenAI  # ASR

from components.gpt_client import ask_gpt
from components.voice import synthesize_voice
from components.mode import MODE_SWITCH_MESSAGES, get_mode_keyboard
from state.session import user_sessions
from handlers.chat.prompt_templates import get_system_prompt
from components.triggers import CREATOR_TRIGGERS, is_strict_say_once_trigger
from components.code_switch import rewrite_mixed_input
from components.profile_db import save_user_profile

# Переводчик: строгая функция перевода
from components.translator import do_translate

# Режим переводчика: дефолты/вход/выход (если файла нет — мягкие заглушки)
try:
    from handlers.translator_mode import ensure_tr_defaults, enter_translator, exit_translator
except Exception:  # файл может отсутствовать в деплое без переводчика
    def ensure_tr_defaults(_): ...
    async def enter_translator(*args, **kwargs): ...
    async def exit_translator(*args, **kwargs): ...

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

# ====================== СТИКЕРЫ + ТРИГГЕРЫ ======================
# ОСТАВЛЯЕМ ТОЛЬКО два стикера: hello (привет) и fire (комплименты). sorry — удалён.
STICKERS = {
    "hello": ["CAACAgIAAxkBAAItV2i269d_71pHUu5Rm9f62vsCW0TrAAJJkAAC96S4SXJs5Yp4uIyENgQ"],
    "fire":  ["CAACAgIAAxkBAAItWWi26-vSBaRPbX6a2imIoWq4Jo0pAALhfwAC6gm5SSTLD1va-EfRNgQ"],
}

# ⚠️ Сохранён для совместимости с импортами (например, из onboarding).
# Делает НИЧЕГО, чтобы бот не слал стикеры сам по себе.
async def maybe_send_sticker(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, key: str, chance: float = 0.35):
    return  # no-op (совместимость)

_GREET_EMOJI = {"👋", "🤝"}
_COMPLIMENT_EMOJI = {"🔥", "💯", "👏", "🌟", "👍", "❤️", "💖", "✨"}

_GREET_WORDS = {
    "hi", "hello", "hey",
    "привет", "здравствуй", "здорово", "хай", "хелло",
    "bonjour", "salut",
    "hola", "buenas",
    "hallo", "servus", "moin",
    "hej", "hejsan", "tjena",
    "hei", "moi", "terve",
}

_COMPLIMENT_STEMS = {
    "great", "awesome", "amazing", "love it", "nice", "cool",
    "класс", "супер", "топ", "круто", "молодец", "огонь",
    "super", "génial", "genial", "top", "formid",
    "genial", "increíble", "increible", "super", "top", "bravo",
    "super", "toll", "klasse", "mega", "geil",
    "super", "grym", "toppen", "snyggt", "bra jobbat",
    "mahtava", "huikea", "upea", "super", "hieno",
}

# «Извини/ошибка» больше не используем для стикеров:
_SORRY_STEMS = set()

def _norm_msg_keep_emoji(s: str) -> str:
    s = (s or "").lower()
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

def _sanitize_user_text(text: str, max_len: int = 2000) -> str:
    text = (text or "").strip()
    if len(text) > max_len:
        text = text[:max_len]
    return text

def _strip_html(s: str) -> str:
    return re.sub(r"<[^>\n]+>", "", unescape(s or ""))

async def _send_voice_or_audio(context: ContextTypes.DEFAULT_TYPE, chat_id: int, file_path: str):
    if file_path.lower().endswith(".ogg"):
        with open(file_path, "rb") as vf:
            await context.bot.send_voice(chat_id=chat_id, voice=vf)
    else:
        with open(file_path, "rb") as af:
            await context.bot.send_audio(chat_id=chat_id, audio=af)

# Шлём стикер ТОЛЬКО на пользовательские сообщения. С анти-флудом per chat.
async def maybe_send_sticker_user(ctx: ContextTypes.DEFAULT_TYPE, update: Update, key: str, chance: float = 0.4):
    try:
        if key not in STICKERS or not STICKERS[key]:
            return
        # Реагируем только на пользователя, не на бота
        if not update.effective_user or (hasattr(ctx, "bot") and update.effective_user.id == ctx.bot.id):
            return

        chat_id = update.effective_chat.id
        sess = user_sessions.setdefault(chat_id, {})
        now = time.time()
        # антифлуд: не чаще 8 сек на чат
        if now < sess.get("next_sticker_at", 0):
            return

        if random.random() < chance:
            await ctx.bot.send_sticker(chat_id=chat_id, sticker=random.choice(STICKERS[key]))
            sess["next_sticker_at"] = now + 8.0
    except Exception:
        logger.debug("send_sticker failed", exc_info=True)

# ====================== ГЛАВНЫЙ ХЕНДЛЕР ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})

    # last seen
    try:
        import datetime as _dt
        save_user_profile(chat_id, last_seen_at=_dt.datetime.utcnow().isoformat())
    except Exception:
        logger.exception("failed to update last_seen_at", exc_info=True)

    # onboarding promo
    try:
        stage = session.get("onboarding_stage")
    except Exception:
        stage = None
    if stage == "awaiting_promo":
        from components.onboarding import promo_code_message
        return await promo_code_message(update, context)

    # rate limiting
    now = time.time()
    if now - session.get("last_message_time", 0) < RATE_LIMIT_SECONDS:
        await context.bot.send_message(chat_id=chat_id, text="⏳ Погоди, думаю 🙂")
        return
    session["last_message_time"] = now

    try:
        # defaults
        session.setdefault("interface_lang", "en")
        session.setdefault("target_lang", "en")
        session.setdefault("level", "A2")
        session.setdefault("mode", "text")
        session.setdefault("style", "casual")
        session.setdefault("task_mode", "chat")
        ensure_tr_defaults(session)

        interface_lang = session["interface_lang"]
        target_lang = session["target_lang"]
        level = session["level"]
        mode = session["mode"]
        style = session["style"]
        translator_cfg = session.get("translator") or {}

        # вход: голос/текст
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
                logger.exception("[Whisper Error]", exc_info=True)
                user_input = ""
            finally:
                try:
                    os.remove(audio_path)
                except Exception:
                    logger.exception("Failed to remove temp audio", exc_info=True)
        else:
            user_input = update.message.text or ""

        user_input = _sanitize_user_text(user_input, max_len=2000)
        if not user_input:
            await context.bot.send_message(chat_id=chat_id, text="❗️Похоже, сообщение не распознано. Скажи что-нибудь ещё 🙂")
            return

        # нормализатор
        def _norm(s: str) -> str:
            s = re.sub(r"[^\w\s]", " ", (s or "").lower())
            s = re.sub(r"\s+", " ", s).strip()
            return s
        msg_norm = _norm(user_input)

        # ===== Переключения text/voice =====
        VOICE_STRICT = {"голос","в голос","в голосовой режим","voice","voice mode"}
        TEXT_STRICT  = {"текст","в текст","в текстовый режим","text","text mode"}

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

        # ===== Вход/выход переводчика =====
        if msg_norm in {"/translator","translator","переводчик","режим переводчика","нужен переводчик","need a translator"}:
            return await enter_translator(update, context, session)
        if msg_norm in {"/translator_off","/translator off","translator off","выйти из переводчика","переводчик выкл"}:
            return await exit_translator(update, context, session)

        # ===== Озвучка последнего ответа (строгий триггер, без smart_say_once_parse) =====
        if is_strict_say_once_trigger(user_input, interface_lang):
            # язык TTS: в переводчике — по направлению, иначе — target_lang
            if session.get("task_mode") == "translator":
                direction = (translator_cfg or {}).get("direction", "ui→target")
                tts_lang = interface_lang if direction == "target→ui" else target_lang
            else:
                tts_lang = target_lang

            last_text = session.get("last_assistant_text")
            if not last_text:
                msg = "Пока нечего озвучивать 😅" if interface_lang == "ru" else "Nothing to voice yet 😅"
                await update.message.reply_text(msg)
                return

            try:
                voice_path = synthesize_voice(last_text, LANGUAGE_CODES.get(tts_lang, "en-US"), level)
                if voice_path:
                    await _send_voice_or_audio(context, chat_id, voice_path)
                else:
                    raise RuntimeError("No TTS data")
            except Exception:
                safe = _strip_html(last_text)
                msg = ("Не удалось озвучить, вот текст:\n" + safe) if interface_lang == "ru" else ("Couldn't voice it; here is the text:\n" + safe)
                logger.exception("[TTS once] failed", exc_info=True)
                await context.bot.send_message(chat_id=chat_id, text=msg)
            return

        # ===== СТИКЕРЫ: реагируем только на слова пользователя (один стикер на сообщение) =====
        if is_greeting(user_input):
            await maybe_send_sticker_user(context, update, "hello", chance=0.45)
        elif is_compliment(user_input):
            await maybe_send_sticker_user(context, update, "fire", chance=0.45)

        # создатель
        norm_for_creator = re.sub(r"[^\w\s]", "", user_input.lower())
        if any(trig in norm_for_creator for trig in CREATOR_TRIGGERS.get(interface_lang, CREATOR_TRIGGERS["en"])):
            reply_text = (
                "🐾 Мой создатель — @marrona! Для обратной связи и предложений к сотрудничеству обращайся прямо к ней. 🌷"
                if interface_lang == "ru"
                else "🐾 My creator is @marrona! For feedback or collaboration offers, feel free to contact her directly. 🌷"
            )
            await update.message.reply_text(reply_text)
            return

        # ======== ВЕТКА: TRANSLATOR MODE — байпас общего чата ========
        if session.get("task_mode") == "translator":
            direction = (translator_cfg or {}).get("direction", "ui→target")
            tr_style  = (translator_cfg or {}).get("style", "casual")
            output    = (translator_cfg or {}).get("output", "text")

            translated = await do_translate(
                user_input,  # в переводчике берём «как есть»
                interface_lang=interface_lang,
                target_lang=target_lang,
                direction=direction,
                style=tr_style,
            )

            assistant_reply = translated or ""
            session["last_assistant_text"] = assistant_reply  # для «озвучь»
            tts_lang = interface_lang if direction == "target→ui" else target_lang

            if output == "voice":
                try:
                    voice_path = synthesize_voice(assistant_reply, LANGUAGE_CODES.get(tts_lang, "en-US"), level)
                    if voice_path:
                        await _send_voice_or_audio(context, chat_id, voice_path)
                    else:
                        raise RuntimeError("No TTS data")
                except Exception:
                    logger.exception("[TR TTS] failed", exc_info=True)
                    safe = _strip_html(assistant_reply or "")
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=("⚠️ Не удалось озвучить, вот текст:\n"+safe) if interface_lang=="ru" else ("⚠️ Couldn't voice; text:\n"+safe)
                    )
            else:
                await update.message.reply_text(assistant_reply, parse_mode=None)
            return

        # === История + промпт (ОБЫЧНЫЙ ЧАТ) ===
        history = session.setdefault("history", [])

        # разовый wrap-up после выхода из переводчика
        wrap_hint = None
        if session.pop("just_left_translator", False):
            wrap_hint = ("You have just exited TRANSLATOR mode. In your next reply (only once), "
                         "you MAY add one very short, upbeat wrap-up line in the TARGET language, "
                         "then continue normal CHAT behavior.")

        system_prompt = get_system_prompt(
            style, level, interface_lang, target_lang, mode,
            task_mode=session.get("task_mode", "chat"),
            translator_cfg=session.get("translator")
        )

        prompt = [{"role": "system", "content": system_prompt}]
        if wrap_hint:
            prompt.append({"role": "system", "content": wrap_hint})
        prompt.extend(history)

        # починка смешанной фразы
        clean_user_input, preface_html = await rewrite_mixed_input(user_input, interface_lang, target_lang)
        prompt.append({"role": "user", "content": clean_user_input})

        assistant_reply = await ask_gpt(prompt, "gpt-4o")

        # история
        history.append({"role": "user", "content": clean_user_input})
        history.append({"role": "assistant", "content": assistant_reply})
        if len(history) > MAX_HISTORY_LENGTH:
            history.pop(0)

        # ====== Постпроцессор: автодубль перевода в скобках (A0–A1, если включено) ======
        append_translation = bool(session.get("append_translation")) and level in {"A0", "A1"}
        final_reply_text = assistant_reply
        ui_side_note = ""

        if append_translation:
            translated = await _translate_for_ui(assistant_reply, interface_lang)
            if translated and _strip_html(translated).lower() != _strip_html(assistant_reply).lower():
                ui_side_note = translated
                final_reply_text = f"{assistant_reply} ({translated})"

        if preface_html:
            final_reply_text = f"{preface_html}\n\n{final_reply_text}"

        # Сохраним основной текст без скобочного дубля — для «озвучь»
        session["last_assistant_text"] = assistant_reply

        # ===== Выбор канала ответа =====
        effective_output = session["mode"]
        if session.get("task_mode") == "translator":
            effective_output = (session.get("translator") or {}).get("output", "text")

        if effective_output == "voice":
            # язык озвучки: в переводчике зависит от направления; иначе target_lang
            if session.get("task_mode") == "translator":
                direction = (translator_cfg or {}).get("direction", "ui→target")
                tts_lang = interface_lang if direction == "target→ui" else target_lang
            else:
                tts_lang = target_lang

            try:
                voice_path = synthesize_voice(assistant_reply, LANGUAGE_CODES.get(tts_lang, "en-US"), level)
                if voice_path:
                    await _send_voice_or_audio(context, chat_id, voice_path)
                else:
                    raise RuntimeError("No TTS data")
            except Exception:
                logger.exception("[TTS reply] failed", exc_info=True)
                await context.bot.send_message(chat_id=chat_id, text="⚠️ Не удалось отправить голос. Вот текст:\n" + _strip_html(final_reply_text))

            # Текст после голоса:
            # - если включён дубль и уровень A0–A1 — отдаём ТОЛЬКО перевод на языке интерфейса (без HTML/эмодзи)
            # - иначе для A0–A2 — как и раньше: отдать текст без HTML (оригинал)
            try:
                if append_translation and ui_side_note:
                    await context.bot.send_message(chat_id=chat_id, text=_strip_html(ui_side_note))
                elif level in ["A0", "A1", "A2"]:
                    await context.bot.send_message(chat_id=chat_id, text=_strip_html(final_reply_text))
            except Exception:
                logger.debug("fallback text after voice failed", exc_info=True)

        else:
            await update.message.reply_text(final_reply_text, parse_mode="HTML")

    except Exception:
        logger.exception("[ОШИБКА в handle_message]", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Что-то пошло не так! Попробуй ещё раз или перезапусти бота командой /start.")

# =============== ЛОКАЛЬНЫЙ ПЕРЕВОДЧИК ДЛЯ ДУБЛЯ UI (A0–A1) ===============
async def _translate_for_ui(text: str, ui_lang: str) -> str:
    """
    Мини-обёртка над ask_gpt для детерминированного перевода в язык интерфейса.
    Возвращает ТОЛЬКО перевод без кавычек и пояснений.
    """
    if not text or not ui_lang:
        return ""
    sys = f"You are a precise translator. Translate the user's message into {ui_lang.upper()} only. Output ONLY the translation. No quotes, no brackets, no commentary, no emojis."
    prompt = [{"role": "system", "content": sys}, {"role": "user", "content": _strip_html(text)}]
    try:
        tr = await ask_gpt(prompt, "gpt-4o-mini")
        tr = (tr or "").strip().strip("«»\"' ").replace("\n", " ")
        return tr
    except Exception:
        logger.exception("[auto-translate] failed", exc_info=True)
        return ""
