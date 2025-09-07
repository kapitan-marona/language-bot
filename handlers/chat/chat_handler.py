import os
import time
import random
import re
import tempfile
import logging
from html import unescape
from telegram import Update
from telegram.ext import ContextTypes

from config.config import ADMINS, OPENAI_API_KEY
from openai import OpenAI  # ASR

from components.gpt_client import ask_gpt
from components.voice import synthesize_voice
from components.mode import MODE_SWITCH_MESSAGES, get_mode_keyboard
from state.session import user_sessions
from handlers.chat.prompt_templates import get_system_prompt
from components.triggers import CREATOR_TRIGGERS, MODE_TRIGGERS
from components.triggers import is_strict_mode_trigger, is_strict_say_once_trigger
from components.code_switch import rewrite_mixed_input
from components.profile_db import save_user_profile

# NEW: переводчик (режим + клавиатура)
from components.translator import get_translator_keyboard, translator_status_text, target_lang_title
from handlers.translator_mode import ensure_tr_defaults, enter_translator, exit_translator

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
STICKERS = {
    "hello": ["CAACAgIAAxkBAAItV2i269d_71pHUu5Rm9f62vsCW0TrAAJJkAAC96S4SXJs5Yp4uIyENgQ"],
    "fire":  ["CAACAgIAAxkBAAItWWi26-vSBaRPbX6a2imIoWq4Jo0pAALhfwAC6gm5SSTLD1va-EfRNgQ"],
    "sorry": ["CAACAgIAAxkBAAItWGi26-jb1_zQAAE1IyLH1XfqWH5aZQAC3oAAAt7vuUlXHMvWZt7gQDYE"],
}

async def maybe_send_sticker(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, key: str, chance: float = 0.35):
    try:
        if key not in STICKERS:
            return
        if random.random() < chance:
            await ctx.bot.send_sticker(chat_id=chat_id, sticker=random.choice(STICKERS[key]))
    except Exception:
        pass

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

_SORRY_STEMS = {
    "sorry", "apolog", "my bad", "wrong", "mistake", "incorrect",
    "you’re wrong", "you are wrong",
    "прости", "извин", "ошиб", "не так", "неправил", "ты ошиб",
    "désolé", "desole", "pardon", "erreur", "faux",
    "perdón", "perdon", "lo siento", "error", "equivoc",
    "sorry", "entschuldig", "fehler", "falsch",
    "förlåt", "forlat", "fel",
    "anteeksi", "virhe", "väärin", "vaarin",
}

# --- триггеры переводчика (вход/выход/подтверждение)
ENTER_PHRASES = {
    "нужен переводчик", "мне нужен переводчик", "переводчик нужен",
    "need a translator", "i need a translator"
}
EXIT_ASK_PHRASES = {
    "как выйти", "как отсюда выйти", "как отключить", "выйти", "выход",
    "how to exit", "how do i exit", "how to leave", "exit", "turn off"
}
YES_PHRASES = {"да", "ага", "ок", "окей", "yes", "yep", "sure"}
NO_PHRASES  = {"нет", "no", "nope"}


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

def is_correction(raw: str) -> bool:
    if not raw:
        return False
    msg = _norm_msg_keep_emoji(raw)
    return any(kw in msg for kw in _SORRY_STEMS)

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

# handlers/chat/chat_handler.py (фрагмент) — готовая функция handle_message

import os
import time
import random
import re
import tempfile
import logging
from html import unescape
from telegram import Update
from telegram.ext import ContextTypes

from config.config import ADMINS, OPENAI_API_KEY
from openai import OpenAI  # ASR

from components.gpt_client import ask_gpt
from components.voice import synthesize_voice
from components.mode import MODE_SWITCH_MESSAGES, get_mode_keyboard
from state.session import user_sessions
from handlers.chat.prompt_templates import get_system_prompt
from components.triggers import CREATOR_TRIGGERS, MODE_TRIGGERS
from components.triggers import is_strict_mode_trigger, is_strict_say_once_trigger
from components.code_switch import rewrite_mixed_input
from components.profile_db import save_user_profile

# NEW: переводчик (режим + клавиатура/тексты)
from components.translator import get_translator_keyboard, translator_status_text, target_lang_title
from handlers.translator_mode import ensure_tr_defaults, enter_translator, exit_translator

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

STICKERS = {
    "hello": ["CAACAgIAAxkBAAItV2i269d_71pHUu5Rm9f62vsCW0TrAAJJkAAC96S4SXJs5Yp4uIyENgQ"],
    "fire":  ["CAACAgIAAxkBAAItWWi26-vSBaRPbX6a2imIoWq4Jo0pAALhfwAC6gm5SSTLD1va-EfRNgQ"],
    "sorry": ["CAACAgIAAxkBAAItWGi26-jb1_zQAAE1IyLH1XfqWH5aZQAC3oAAAt7vuUlXHMvWZt7gQDYE"],
}

def _norm_msg_keep_emoji(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^\w\s\u0400-\u04FF\u00C0-\u024F\u1F300-\u1FAFF]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def is_greeting(raw: str) -> bool:
    if not raw:
        return False
    if any(e in raw for e in {"👋","🤝"}):
        return True
    words = set(_norm_msg_keep_emoji(raw).split())
    return any(w in words for w in {
        "hi","hello","hey","привет","здравствуй","здорово","хай","хелло",
        "bonjour","salut","hola","buenas","hallo","servus","moin",
        "hej","hejsan","tjena","hei","moi","terve"
    })

def is_compliment(raw: str) -> bool:
    if not raw:
        return False
    if any(e in raw for e in {"🔥","💯","👏","🌟","👍","❤️","💖","✨"}):
        return True
    msg = _norm_msg_keep_emoji(raw)
    return any(kw in msg for kw in {
        "great","awesome","amazing","love it","nice","cool",
        "класс","супер","топ","круто","молодец","огонь",
        "super","génial","genial","top","formid",
        "increíble","increible","bravo",
        "toll","klasse","mega","geil",
        "grym","toppen","snyggt","bra jobbat",
        "mahtava","huikea","upea","hieno",
    })

def is_correction(raw: str) -> bool:
    if not raw:
        return False
    msg = _norm_msg_keep_emoji(raw)
    return any(kw in msg for kw in {
        "sorry","apolog","my bad","wrong","mistake","incorrect","you’re wrong","you are wrong",
        "прости","извин","ошиб","не так","неправил","ты ошиб",
        "désolé","desole","pardon","erreur","faux",
        "perdón","perdon","lo siento","error","equivoc",
        "entschuldig","fehler","falsch",
        "förlåt","forlat","fel",
        "anteeksi","virhe","väärin","vaarin",
    })

def _sanitize_user_text(text: str, max_len: int = 2000) -> str:
    text = (text or "").strip()
    if len(text) > max_len:
        text = text[:max_len]
    return text

def _strip_html(s: str) -> str:
    return re.sub(r"<[^>\n]+>", "", unescape(s or ""))

async def maybe_send_sticker(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, key: str, chance: float = 0.35):
    try:
        if key in STICKERS and random.random() < chance:
            await ctx.bot.send_sticker(chat_id=chat_id, sticker=random.choice(STICKERS[key]))
    except Exception:
        # стикеры — не критично
        logger.debug("send_sticker failed", exc_info=True)

async def _send_voice_or_audio(context: ContextTypes.DEFAULT_TYPE, chat_id: int, file_path: str):
    if file_path.lower().endswith(".ogg"):
        with open(file_path, "rb") as vf:
            await context.bot.send_voice(chat_id=chat_id, voice=vf)
    else:
        with open(file_path, "rb") as af:
            await context.bot.send_audio(chat_id=chat_id, audio=af)

# --- «умный» парсер команды озвучки (инлайн или последний ответ)
def smart_say_once_parse(raw: str, ui: str, say_triggers: dict) -> dict | None:
    """
    Возвращает:
      - {"mode": "inline", "text": "..."} — если нашли текст после команды (озвучить ЭТО)
      - {"mode": "last"} — если команда есть, но текста после неё нет (озвучить ПОСЛЕДНИЙ ответ)
      - None — если это вообще не команда озвучки
    """
    if not raw:
        return None

    arr = (say_triggers.get(ui, []) or []) + (say_triggers.get("en", []) or [])
    if not arr:
        return None

    # подготовим альтернативы
    trig_alt = "|".join(sorted([re.escape(t.lower()) for t in arr], key=len, reverse=True))
    polite_ru = r"(?:пожалуйста|пж|пжлст|будь добр|будь добра)"
    polite_en = r"(?:please|pls|plz|could you|would you)"
    polite_any = rf"(?:{polite_ru}|{polite_en})"
    raw_l = (raw or "").strip()

    # 1) Инлайн-команда в начале строки: <вежл?> <триггер> <вежл?> [:,-–—]? "текст" | остаток строки
    inline_pat = re.compile(
        rf"""^\s*(?:{polite_any}\s+)?(?:{trig_alt})\s*(?:{polite_any}\s*)?
             [:\-,–—]?\s*
             (?:
                ["“](.+?)["”]      # в кавычках
                |
                (.+)               # либо весь остаток
             )\s*$""",
        re.IGNORECASE | re.VERBOSE | re.UNICODE,
    )
    m = inline_pat.match(raw_l)
    if m:
        text = (m.group(1) or m.group(2) or "").strip()
        if text and text.lower() not in {"это","this","that"}:
            return {"mode": "inline", "text": text}
        return {"mode": "last"}

    # 2) Короткая команда — вся строка только «say it/озвучь…»
    short_pat = re.compile(
        rf"""^\s*(?:{polite_any}\s+)?(?:{trig_alt})(?:\s+{polite_any})?\s*[!\.\u2764-\U0010FFFF]*\s*$""",
        re.IGNORECASE | re.VERBOSE | re.UNICODE,
    )
    if short_pat.match(raw_l):
        return {"mode": "last"}

    return None

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

        # ===== Озвучка: инлайн или последний ответ (перехват ДО GPT) =====
        from components.triggers import SAY_ONCE_TRIGGERS
        say_cmd = smart_say_once_parse(user_input, interface_lang, SAY_ONCE_TRIGGERS)
        if say_cmd:
            # выбираем язык TTS: в переводчике — по направлению, иначе — target_lang
            if session.get("task_mode") == "translator":
                direction = (translator_cfg or {}).get("direction", "ui→target")
                tts_lang = interface_lang if direction == "target→ui" else target_lang
            else:
                tts_lang = target_lang

            try:
                if say_cmd["mode"] == "inline":
                    text_to_voice = say_cmd["text"]
                else:
                    last_text = session.get("last_assistant_text")
                    if not last_text:
                        msg = "Пока нечего озвучивать 😅" if interface_lang == "ru" else "Nothing to voice yet 😅"
                        await update.message.reply_text(msg)
                        return
                    text_to_voice = last_text

                voice_path = synthesize_voice(text_to_voice, LANGUAGE_CODES.get(tts_lang, "en-US"), level)
                if voice_path:
                    await _send_voice_or_audio(context, chat_id, voice_path)
                else:
                    raise RuntimeError("No TTS data")
            except Exception:
                safe = _strip_html(text_to_voice if say_cmd["mode"] == "inline" else session.get("last_assistant_text", ""))
                msg = ("Не удалось озвучить, вот текст:\n" + safe) if interface_lang == "ru" else ("Couldn't voice it; here is the text:\n" + safe)
                logger.exception("[TTS once] failed", exc_info=True)
                await context.bot.send_message(chat_id=chat_id, text=msg)
            return

        # стикеры
        if is_greeting(user_input):
            await maybe_send_sticker(context, chat_id, "hello", chance=0.4)
        if is_compliment(user_input):
            await maybe_send_sticker(context, chat_id, "fire", chance=0.35)
        if is_correction(user_input):
            await maybe_send_sticker(context, chat_id, "sorry", chance=0.35)

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

        # === История + промпт ===
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

        final_reply_text = f"{preface_html}\n\n{assistant_reply}" if preface_html else assistant_reply

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
            # для низких уровней — дублим чистый текст без HTML
            if level in ["A0","A1","A2"]:
                try:
                    await context.bot.send_message(chat_id=chat_id, text=_strip_html(final_reply_text))
                except Exception:
                    logger.debug("fallback text after voice failed", exc_info=True)
            session["last_assistant_text"] = assistant_reply
        else:
            await update.message.reply_text(final_reply_text, parse_mode="HTML")
            session["last_assistant_text"] = assistant_reply

    except Exception:
        logger.exception("[ОШИБКА в handle_message]", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Что-то пошло не так! Попробуй ещё раз или перезапусти бота командой /start.")
