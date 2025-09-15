# handlers/chat/chat_handler.py
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from html import unescape
from typing import Dict, List

from telegram import Update
from telegram.ext import ContextTypes

from state.session import user_sessions
from components.gpt_client import ask_gpt
from components.mode import MODE_SWITCH_MESSAGES, get_mode_keyboard
from components.stickers_service import maybe_send_thematic_sticker
from components.translator import do_translate
from components.voice_async import speech_to_text_async, synthesize_voice_async
from components.rate_limit import async_rate_limit
from components.history import get_history, append_history
from components.profile_db import save_user_profile
from handlers.chat.prompt_templates import get_system_prompt
from components.triggers import CREATOR_TRIGGERS, is_strict_say_once_trigger
from components.code_switch import rewrite_mixed_input

logger = logging.getLogger(__name__)

MAX_HISTORY_LENGTH = 16
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


@dataclass
class ChatCfg:
    interface_lang: str = "en"
    target_lang: str = "en"
    level: str = "A2"
    mode: str = "text"  # text|voice
    style: str = "casual"
    task_mode: str = "chat"  # chat|translator


# ====================== УТИЛИТЫ ======================
def _sanitize_user_text(text: str, max_len: int = 2000) -> str:
    text = (text or "").strip()
    return text[:max_len]


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>\n]+>", "", unescape(s or ""))


def _norm_cmd(s: str) -> str:
    s = re.sub(r"[^\w\s]", " ", (s or "").lower())
    s = re.sub(r"\s+", " ", s).strip()
    return s


async def _send_voice_or_audio(context: ContextTypes.DEFAULT_TYPE, chat_id: int, file_path: str):
    with open(file_path, "rb") as f:
        if file_path.lower().endswith(".ogg"):
            await context.bot.send_voice(chat_id=chat_id, voice=f)
        else:
            await context.bot.send_audio(chat_id=chat_id, audio=f)

def _enforce_gentle_correction_limits(user_text: str, assistant_html: str) -> str:
    """
    Страховка от 'перекоррекции':
      • не допускаем длинного 'эха' пользователя,
      • ограничиваем число <b>…</b> до 3,
      • убираем гипер-развёрнутые 'правила' длиной > ~500 символов в одном куске.
    Никакой 'переписки' смысла ответа — только мягкая чистка.
    """
    if not assistant_html:
        return assistant_html

    text = assistant_html

    # 1) Срежем длинные кавычки/цитаты пользователя (эхо > 60% длины исхода)
    ut = (user_text or "").strip()
    if ut:
        uclean = re.sub(r"\s+", " ", ut).strip().lower()
        tclean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip().lower()
        if len(uclean) >= 12 and uclean in tclean and len(uclean) / max(1, len(tclean)) > 0.6:
            # удалим прямую вставку исходной фразы в ответе
            pattern = re.escape(ut)
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # 2) Ограничим число жирных замен до 3
    #    оставляем первые 3 <b>…</b>, остальные разжирняем (снимаем теги)
    def _strip_b_tags(s: str) -> str:
        s = re.sub(r"</b\s*>", "", s, flags=re.IGNORECASE)
        s = re.sub(r"<b\s*>", "", s, flags=re.IGNORECASE)
        return s

    bold_spans = list(re.finditer(r"<b[^>]*>.*?</b>", text, flags=re.IGNORECASE | re.DOTALL))
    if len(bold_spans) > 3:
        # снимаем жирность со всех после первых трёх
        kept = 0
        out = []
        i = 0
        while i < len(text):
            m = re.search(r"<b[^>]*>.*?</b>", text[i:], flags=re.IGNORECASE | re.DOTALL)
            if not m:
                out.append(text[i:])
                break
            start = i + m.start()
            end   = i + m.end()
            out.append(text[i:start])
            segment = text[start:end]
            if kept < 3:
                out.append(segment)
                kept += 1
            else:
                out.append(_strip_b_tags(segment))
            i = end
        text = "".join(out)

    # 3) Слишком длинные "разборы ошибок" (куски > 500 символов) — режем до 500
    text = re.sub(r"(.{500,}?)(\n|$)", lambda m: m.group(1)[:500] + (m.group(2) or ""), text)

    return text


# ====================== ГЛАВНЫЙ ХЕНДЛЕР ======================
@async_rate_limit(RATE_LIMIT_SECONDS)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})

    _ensure_defaults(session)
    asyncio.create_task(_update_last_seen(chat_id))  # неблокирующе

    # онбординг-промо: пропускаем в соответствующий хендлер
    if session.get("onboarding_stage") == "awaiting_promo":
        from components.onboarding import promo_code_message
        return await promo_code_message(update, context)

    # вход: текст/голос (ASR — async фасад, не блокирует loop)
    user_input = await _read_user_input(update, context)
    user_input = _sanitize_user_text(user_input)
    if not user_input:
        return await context.bot.send_message(chat_id=chat_id, text="❗️Похоже, сообщение не распознано. Скажи что-нибудь ещё 🙂")

    cfg = _cfg_from_session(session)
    msg_norm = _norm_cmd(user_input)

    # строгие переключатели режимов
    if await _maybe_switch_mode(update, session, cfg, msg_norm):
        return

    # вход/выход переводчика
    if await _maybe_toggle_translator(update, context, session, msg_norm):
        return

    # озвучить последний ответ (say-once)
    if is_strict_say_once_trigger(user_input, cfg.interface_lang):
        return await _say_last_once(context, chat_id, session, cfg)

    # стикеры (антифлуд и шанс внутри сервиса)
    history = get_history(session, maxlen=MAX_HISTORY_LENGTH)
    await maybe_send_thematic_sticker(context, update, session, list(history), user_input)

    # создатель
    if _hits_creator(user_input, cfg.interface_lang):
        txt = (
            "🐾 Мой создатель — @marrona! Для обратной связи и предложений к сотрудничеству обращайся прямо к ней. 🌷"
            if cfg.interface_lang == "ru" else
            "🐾 My creator is @marrona! For feedback or collaboration offers, feel free to contact her directly. 🌷"
        )
        return await update.message.reply_text(txt)

    # ======= Ветка переводчика (байпас) =======
    if session.get("task_mode") == "translator":
        return await _run_translator_flow(update, context, session, cfg, user_input, chat_id)

    # ======= Обычный чат =======
    wrap_hint = None
    if session.pop("just_left_translator", False):
        wrap_hint = ("You have just exited TRANSLATOR mode. In your next reply (only once), "
                     "you MAY add one very short, upbeat wrap-up line in the TARGET language, "
                     "then continue normal CHAT behavior.")

    system_prompt = get_system_prompt(
        cfg.style, cfg.level, cfg.interface_lang, cfg.target_lang, cfg.mode,
        task_mode=session.get("task_mode", "chat"),
        translator_cfg=session.get("translator")
    )

    prompt: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if wrap_hint:
        prompt.append({"role": "system", "content": wrap_hint})
    prompt.extend(list(history))  # deque → list

    clean_user_input, preface_html = await rewrite_mixed_input(user_input, cfg.interface_lang, cfg.target_lang)
    prompt.append({"role": "user", "content": clean_user_input})

    # GPT: с таймаутом, чтобы не подвисал хендлер
    try:
        assistant_reply = await asyncio.wait_for(ask_gpt(prompt, "gpt-4o"), timeout=45)
    except asyncio.TimeoutError:
        logger.warning("ask_gpt timeout")
        return await context.bot.send_message(chat_id=chat_id, text="⚠️ Сервер отвечает дольше обычного. Попробуй ещё раз.")

    append_history(session, "user", clean_user_input)
    append_history(session, "assistant", assistant_reply)

    # A0/A1 — автодубль перевода в скобках (если включено)
    final_reply_text = assistant_reply
    ui_side_note = ""
    if bool(session.get("append_translation")) and cfg.level in {"A0", "A1"}:
        tr = await _translate_for_ui(assistant_reply, cfg.interface_lang)
        clean_a = _strip_html(assistant_reply).lower()
        clean_b = _strip_html(tr).lower()
        if tr and clean_a != clean_b:
            ui_side_note = tr
            final_reply_text = f"{assistant_reply} ({tr})"

    if preface_html:
        final_reply_text = f"{preface_html}\n\n{final_reply_text}"

    session["last_assistant_text"] = assistant_reply
    # Страховка от 'перекоррекции'
    final_reply_text = _enforce_gentle_correction_limits(clean_user_input, final_reply_text)

    # Канал ответа: voice или text
    if cfg.mode == "voice":
        await _send_voice_reply(context, chat_id, session, cfg, assistant_reply, final_reply_text, ui_side_note)
    else:
        await update.message.reply_text(final_reply_text, parse_mode="HTML")


# ====================== ПОДФУНКЦИИ ======================
async def _update_last_seen(chat_id: int):
    try:
        import datetime as _dt
        await asyncio.to_thread(save_user_profile, chat_id, last_seen_at=_dt.datetime.utcnow().isoformat())
    except Exception:
        logger.debug("failed to update last_seen_at", exc_info=True)


async def _read_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    if update.message.voice:
        try:
            tg_file = await context.bot.get_file(update.message.voice.file_id)
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tf:
                await tg_file.download_to_drive(tf.name)
                path = tf.name
            try:
                text = await speech_to_text_async(path)
                return (text or "").strip()
            finally:
                try:
                    os.remove(path)
                except Exception:
                    logger.debug("temp cleanup failed", exc_info=True)
        except Exception:
            logger.exception("ASR error")
            return ""
    return update.message.text or ""


async def _maybe_switch_mode(update: Update, session: Dict, cfg: ChatCfg, msg_norm: str) -> bool:
    VOICE_STRICT = {"голос", "в голос", "в голосовой режим", "voice", "voice mode"}
    TEXT_STRICT = {"текст", "в текст", "в текстовый режим", "text", "text mode"}

    if msg_norm in VOICE_STRICT:
        if session.get("mode") != "voice":
            session["mode"] = "voice"
            msg = MODE_SWITCH_MESSAGES["voice"].get(cfg.interface_lang, MODE_SWITCH_MESSAGES["voice"]["en"])
            await update.message.reply_text(msg, reply_markup=get_mode_keyboard("voice", cfg.interface_lang))
        return True
    if msg_norm in TEXT_STRICT:
        if session.get("mode") != "text":
            session["mode"] = "text"
            msg = MODE_SWITCH_MESSAGES["text"].get(cfg.interface_lang, MODE_SWITCH_MESSAGES["text"]["en"])
            await update.message.reply_text(msg, reply_markup=get_mode_keyboard("text", cfg.interface_lang))
        return True
    return False


async def _maybe_toggle_translator(update: Update, context: ContextTypes.DEFAULT_TYPE, session: Dict, msg_norm: str) -> bool:
    try:
        from handlers.translator_mode import ensure_tr_defaults, enter_translator, exit_translator
    except Exception:
        def ensure_tr_defaults(_): ...
        async def enter_translator(*args, **kwargs): ...
        async def exit_translator(*args, **kwargs): ...
    ensure_tr_defaults(session)
    if msg_norm in {"/translator", "translator", "переводчик", "режим переводчика", "нужен переводчик", "need a translator"}:
        await enter_translator(update, context, session)
        return True
    if msg_norm in {"/translator_off", "/translator off", "translator off", "выйти из переводчика", "переводчик выкл"}:
        await exit_translator(update, context, session)
        return True
    return False


async def _say_last_once(context: ContextTypes.DEFAULT_TYPE, chat_id: int, session: Dict, cfg: ChatCfg):
    if session.get("task_mode") == "translator":
        direction = (session.get("translator") or {}).get("direction", "ui→target")
        tts_lang = cfg.interface_lang if direction == "target→ui" else cfg.target_lang
    else:
        tts_lang = cfg.target_lang

    last_text = session.get("last_assistant_text")
    if not last_text:
        msg = "Пока нечего озвучивать 😅" if cfg.interface_lang == "ru" else "Nothing to voice yet 😅"
        return await context.bot.send_message(chat_id=chat_id, text=msg)

    try:
        path = await synthesize_voice_async(last_text, LANGUAGE_CODES.get(tts_lang, "en-US"), cfg.level)
        await _send_voice_or_audio(context, chat_id, path)
    except Exception:
        logger.exception("[TTS once] failed")
        safe = _strip_html(last_text)
        msg = ("Не удалось озвучить, вот текст:\n" + safe) if cfg.interface_lang == "ru" else ("Couldn't voice it; here is the text:\n" + safe)
        await context.bot.send_message(chat_id=chat_id, text=msg)


def _hits_creator(user_input: str, interface_lang: str) -> bool:
    norm = re.sub(r"[^\w\s]", "", (user_input or "").lower())
    return any(tr in norm for tr in CREATOR_TRIGGERS.get(interface_lang, CREATOR_TRIGGERS["en"]))


async def _run_translator_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, session: Dict, cfg: ChatCfg, user_input: str, chat_id: int):
    translator_cfg = session.get("translator") or {}
    direction = translator_cfg.get("direction", "ui→target")
    tr_style  = translator_cfg.get("style", "casual")
    output    = translator_cfg.get("output", "text")

    translated = await do_translate(
        user_input,
        interface_lang=cfg.interface_lang,
        target_lang=cfg.target_lang,
        direction=direction,
        style=tr_style,
        level=cfg.level,        # ← важно
        output=output,          # ← важно
    )

    translated = (translated or "").strip()
    session["last_assistant_text"] = translated

    tts_lang = cfg.interface_lang if direction == "target→ui" else cfg.target_lang
    if output == "voice":
        try:
            path = await synthesize_voice_async(translated, LANGUAGE_CODES.get(tts_lang, "en-US"), cfg.level)
            await _send_voice_or_audio(context, chat_id, path)
        except Exception:
            safe = _strip_html(translated)
            await context.bot.send_message(
                chat_id=chat_id,
                text=("⚠️ Не удалось озвучить, вот текст:\n" + safe) if cfg.interface_lang == "ru"
                     else ("⚠️ Couldn't voice; text:\n" + safe)
            )
    else:
        await update.message.reply_text(translated, parse_mode=None)


async def _send_voice_reply(context: ContextTypes.DEFAULT_TYPE, chat_id: int, session: Dict, cfg: ChatCfg, assistant_reply: str, final_reply_text: str, ui_side_note: str):
    try:
        path = await synthesize_voice_async(assistant_reply, LANGUAGE_CODES.get(cfg.target_lang, "en-US"), cfg.level)
        await _send_voice_or_audio(context, chat_id, path)
    except Exception:
        logger.debug("[TTS reply] failed", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Не удалось отправить голос. Вот текст:\n" + _strip_html(final_reply_text))
        return

    # Текст после голоса — только когда действительно нужен
    try:
        if ui_side_note:
            await context.bot.send_message(chat_id=chat_id, text=_strip_html(ui_side_note))
        elif cfg.level in ["A0", "A1", "A2"]:
            await context.bot.send_message(chat_id=chat_id, text=_strip_html(final_reply_text))
    except Exception:
        logger.debug("fallback text after voice failed", exc_info=True)


def _ensure_defaults(session: Dict):
    session.setdefault("interface_lang", "en")
    session.setdefault("target_lang", "en")
    session.setdefault("level", "A2")
    session.setdefault("mode", "text")
    session.setdefault("style", "casual")
    session.setdefault("task_mode", "chat")


def _cfg_from_session(session: Dict) -> ChatCfg:
    return ChatCfg(
        interface_lang=session.get("interface_lang", "en"),
        target_lang=session.get("target_lang", "en"),
        level=session.get("level", "A2"),
        mode=session.get("mode", "text"),
        style=session.get("style", "casual"),
        task_mode=session.get("task_mode", "chat"),
    )


async def _translate_for_ui(text: str, ui_lang: str) -> str:
    if not text or not ui_lang:
        return ""
    sys = f"You are a precise translator. Translate the user's message into {ui_lang.upper()} only. Output ONLY the translation. No quotes, no brackets, no commentary, no emojis."
    prompt = [{"role": "system", "content": sys}, {"role": "user", "content": _strip_html(text)}]
    try:
        tr = await ask_gpt(prompt, "gpt-4o-mini")
        return (tr or "").strip().strip("«»\"' ").replace("\n", " ")
    except Exception:
        logger.debug("[auto-translate] failed", exc_info=True)
        return ""
