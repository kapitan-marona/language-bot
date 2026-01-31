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

# === NEW: персистентная история в БД ===
from components.profile_db import save_message, load_last_messages  # NEW

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
    if not assistant_html:
        return assistant_html
    text = assistant_html
    ut = (user_text or "").strip()
    if ut:
        uclean = re.sub(r"\s+", " ", ut).strip().lower()
        tclean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip().lower()
        if len(uclean) >= 12 and uclean in tclean and len(uclean) / max(1, len(tclean)) > 0.6:
            pattern = re.escape(ut)
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    def _strip_b_tags(s: str) -> str:
        s = re.sub(r"</b\s*>", "", s, flags=re.IGNORECASE)
        s = re.sub(r"<b\s*>", "", s, flags=re.IGNORECASE)
        return s
    bold_spans = list(re.finditer(r"<b[^>]*>.*?</b>", text, flags=re.IGNORECASE | re.DOTALL))
    if len(bold_spans) > 3:
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
    text = re.sub(r"(.{500,}?)(\n|$)", lambda m: m.group(1)[:500] + (m.group(2) or ""), text)
    return text

def _get_cfg(session: Dict) -> ChatCfg:
    cfg = ChatCfg()
    st = (session or {}).get("settings") or {}
    cfg.interface_lang = (st.get("interface_lang") or "en").lower()
    cfg.target_lang = (st.get("target_lang") or "en").lower()
    cfg.level = (st.get("level") or "A2").upper()
    cfg.mode = (st.get("mode") or "text").lower()
    cfg.style = (st.get("style") or "casual").lower()
    cfg.task_mode = (st.get("task_mode") or "chat").lower()
    return cfg

def _hits_creator(user_text: str, ui_lang: str) -> bool:
    t = _norm_cmd(user_text)
    phrases = CREATOR_TRIGGERS.get(ui_lang, []) + CREATOR_TRIGGERS.get("en", [])
    for p in phrases:
        if _norm_cmd(p) in t:
            return True
    return False

async def _say_last_once(context: ContextTypes.DEFAULT_TYPE, chat_id: int, session: Dict, cfg: ChatCfg):
    last = session.get("last_reply_once")
    if not last:
        return
    try:
        if cfg.mode == "voice":
            # Озвучим текст голосом
            lang = LANGUAGE_CODES.get(cfg.interface_lang, "en-US")
            file_path = await synthesize_voice_async(last, lang=lang)
            await _send_voice_or_audio(context, chat_id, file_path)
        else:
            await context.bot.send_message(chat_id=chat_id, text=last)
    except Exception:
        logger.exception("say_last_once failed")

# ====================== ГЛАВНЫЙ ХЕНДЛЕР ======================
@async_rate_limit(RATE_LIMIT_SECONDS)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.effective_chat:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    session = user_sessions.get(user_id)
    if not session:
        session = {"settings": {}, "history": [], "usage": {}}
        user_sessions[user_id] = session

    cfg = _get_cfg(session)

    user_input = ""
    if update.message and update.message.text:
        user_input = update.message.text
    elif update.message and update.message.voice:
        lang = LANGUAGE_CODES.get(cfg.interface_lang, "en-US")
        user_input = await speech_to_text_async(update, context, lang=lang)
    else:
        return

    user_input = (user_input or "").strip()
    if not user_input:
        return

    # слегка почистим
    user_input = _sanitize_user_text(user_input)

    # если пользователь пишет смешанным языком — перепишем в один (мягко)
    try:
        rewritten, preface_html = await rewrite_mixed_input(
            user_input, cfg.interface_lang, cfg.target_lang
        )
        if preface_html:
            # коротко покажем пользователю, что мы поняли (не обязательно, но логика в code_switch именно для этого)
            await update.message.reply_html(preface_html)
        user_input = rewritten
    except Exception:
        pass

    msg_norm = _norm_cmd(user_input)


    # показать меню переключения режима
    if msg_norm in {"/mode", "mode", "режим"}:
        txt = MODE_SWITCH_MESSAGES.get(cfg.interface_lang, MODE_SWITCH_MESSAGES["en"])
        await update.message.reply_text(txt, reply_markup=get_mode_keyboard(cfg.mode, cfg.interface_lang))
        return

    # "последнее" / озвучь
    if msg_norm in {"/last", "last", "повтори", "повтори последнее"} or is_strict_say_once_trigger(user_input, cfg.interface_lang):
        return await _say_last_once(context, chat_id, session, cfg)

    # ✅ СТИКЕРЫ: отключаем в режиме переводчика
    # стикеры (антифлуд и шанс внутри сервиса)
    if cfg.task_mode != "translator":
        history = get_history(session, maxlen=MAX_HISTORY_LENGTH)
        await maybe_send_thematic_sticker(context, update, session, list(history), user_input)

    # создатель
    if _hits_creator(user_input, cfg.interface_lang):
        txt = (
            "🐾 Мой создатель — @marrona! Для обратной связи и предложений к сотрудничеству обращайся прямо к нему."
            if cfg.interface_lang == "ru"
            else "🐾 My creator is @marrona! For feedback or collaboration ideas, contact them directly."
        )
        await update.message.reply_text(txt, reply_markup=get_mode_keyboard(cfg.mode, cfg.interface_lang))
        session["last_reply_once"] = txt
        return

    # === переводчик vs чат ===
    if cfg.task_mode == "translator":
        direction = (session.get("translator") or {}).get("direction", "ui→target")
        tr_style = (session.get("translator") or {}).get("style", cfg.style)

        out = await do_translate(
            user_input,
            interface_lang=cfg.interface_lang,
            target_lang=cfg.target_lang,
            direction=direction,
            style=tr_style,
            level=cfg.level,
            output="voice" if cfg.mode == "voice" else "text",
        )

        if cfg.mode == "voice":
            tts_lang = LANGUAGE_CODES.get(cfg.target_lang, LANGUAGE_CODES.get(cfg.interface_lang, "en-US"))
            file_path = await synthesize_voice_async(out, lang=tts_lang)
            await _send_voice_or_audio(context, chat_id, file_path)
        else:
            await update.message.reply_text(out)

        session["last_reply_once"] = out
        return

    # === обычный чат ===
    # загрузка последних сообщений из БД (персистентная история)
    try:
        persisted = load_last_messages(user_id, limit=MAX_HISTORY_LENGTH)
        session["history"] = persisted or session.get("history", [])
    except Exception:
        pass

    history = get_history(session, maxlen=MAX_HISTORY_LENGTH)

    system_prompt = get_system_prompt(
        interface_lang=cfg.interface_lang,
        target_lang=cfg.target_lang,
        level=cfg.level,
        style=cfg.style,
        mode=cfg.mode,
    )

    messages = [{"role": "system", "content": system_prompt}]
    for h in history:
        if h.get("role") in {"user", "assistant"} and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_input})

    reply_html = await ask_gpt(messages, model="gpt-4o-mini", temperature=0.7, max_tokens=550)
    reply_html = (reply_html or "").strip()
    reply_html = _enforce_gentle_correction_limits(user_input, reply_html)

    # обновим историю в памяти
    append_history(session, "user", user_input, maxlen=MAX_HISTORY_LENGTH)
    append_history(session, "assistant", reply_html, maxlen=MAX_HISTORY_LENGTH)

    # сохраним в БД
    try:
        save_message(user_id, "user", user_input)
        save_message(user_id, "assistant", reply_html)
    except Exception:
        pass

    # обновим профиль
    try:
        save_user_profile(user_id, session.get("settings", {}))
    except Exception:
        logger.debug("save_user_profile failed", exc_info=True)

    # ответ пользователю
    if cfg.mode == "voice":
        lang = LANGUAGE_CODES.get(cfg.interface_lang, "en-US")
        # TTS озвучиваем ТЕКСТ без HTML
        voice_text = _strip_html(reply_html)
        file_path = await synthesize_voice_async(voice_text, lang=lang)
        await _send_voice_or_audio(context, chat_id, file_path)
    else:
        await update.message.reply_html(reply_html, reply_markup=get_mode_keyboard(cfg.mode, cfg.interface_lang))

    session["last_reply_once"] = _strip_html(reply_html)
