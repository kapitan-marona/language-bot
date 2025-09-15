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

# ✅ Новое: конфиг стикеров и приоритет
from components.stickers import STICKERS_CONFIG, STICKERS_PRIORITY

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

# ====================== УТИЛИТЫ ======================
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

def _normalize_for_triggers(s: str) -> str:
    s = (s or "").lower()
    # латиница/кириллица/европ. акценты оставляем; выкидываем пунктуацию
    s = re.sub(r"[^\w\s\u0400-\u04FF\u00C0-\u024F]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _match_sticker_key(user_raw: str) -> str | None:
    """
    Возвращает ключ стикера из STICKERS_CONFIG согласно приоритету
    или None, если триггера нет.
    """
    raw = user_raw or ""
    norm = _normalize_for_triggers(raw)

    for key in STICKERS_PRIORITY:
        cfg = STICKERS_CONFIG.get(key) or {}
        # Эмодзи — ищем в "сыром" тексте
        for emo in cfg.get("emoji", []):
            if emo and emo in raw:
                return key
        # Фразы — ищем по нормализованной строке (как подстроку)
        for trig in cfg.get("triggers", []):
            t = _normalize_for_triggers(trig)
            if t and t in norm:
                return key
    return None

async def maybe_send_sticker_thematic(context: ContextTypes.DEFAULT_TYPE, update: Update, session: dict, history: list, user_text: str):
    """
    1) Антифлуд: не больше 1 стикера в окне из 40 реплик истории.
    2) Вероятность 30% при сработавшем триггере.
    3) Отправляет стикер и ничего не возвращает (основной ответ всё равно идёт текстом по обычной логике).
    """
    # 1) окно истории
    last_idx = session.get("last_sticker_hist_idx")
    hist_len = len(history or [])
    if isinstance(last_idx, int) and (hist_len - last_idx) < 40:
        return  # уже был стикер в текущем окне из 40 сообщений

    # 2) матч триггера
    key = _match_sticker_key(user_text)
    if not key:
        return

    # 3) вероятность 30%
    if random.random() >= 0.30:
        return

    # 4) отправка
    file_id = (STICKERS_CONFIG.get(key) or {}).get("id")
    if not file_id:
        return
    try:
        await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=file_id)
        session["last_sticker_hist_idx"] = hist_len  # запомнить позицию
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

        # ===== СТИКЕРЫ: тематические (антифлуд 1/40, шанс 30%) =====
        # Нужна история для окна 40 — создаём её заранее
        history = session.setdefault("history", [])
        await maybe_send_sticker_thematic(context, update, session, history, user_input)

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
        # history уже создан выше
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
