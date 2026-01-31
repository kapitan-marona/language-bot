# handlers/chat/chat_handler.py
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
from components.triggers import (
    detect_language_switch,
    detect_level_switch,
    detect_style_switch,
    detect_mode_switch,
)
from utils.decorators import safe_handler

logger = logging.getLogger(__name__)

MAX_HISTORY_LENGTH = 40

VOICE_LANGS = {
    "en": "en-US",
    "ru": "ru-RU",
    "de": "de-DE",
    "fr": "fr-FR",
    "es": "es-ES",
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
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_len:
        text = text[:max_len].rstrip() + "…"
    return text

def _norm_msg(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t

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

async def _say_last_once(context: ContextTypes.DEFAULT_TYPE, chat_id: int, session: Dict, cfg: ChatCfg):
    last = session.get("last_reply_once")
    if last:
        try:
            if cfg.mode == "voice":
                await context.bot.send_message(chat_id=chat_id, text=last, reply_markup=get_mode_keyboard("voice", cfg.interface_lang))
            else:
                await context.bot.send_message(chat_id=chat_id, text=last, reply_markup=get_mode_keyboard("text", cfg.interface_lang))
        except Exception:
            logger.debug("say_last_once failed", exc_info=True)

async def _maybe_process_mode_commands(update: Update, context: ContextTypes.DEFAULT_TYPE, session: Dict, msg_norm: str, cfg: ChatCfg) -> bool:
    if msg_norm in {"/mode", "mode", "режим"}:
        txt = MODE_SWITCH_MESSAGES.get(cfg.interface_lang, MODE_SWITCH_MESSAGES["en"])
        await update.message.reply_text(txt, reply_markup=get_mode_keyboard(cfg.mode, cfg.interface_lang))
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
    if msg_norm in {"/translator", "translator", "переводчик", "режим переводчика"}:
        await enter_translator(update, context)
        return True
    if msg_norm in {"/translator_off", "/translation_off", "translator off", "выключи переводчик"}:
        await exit_translator(update, context)
        return True
    return False

def _hits_creator(text: str, ui_lang: str) -> bool:
    t = (text or "").lower()
    if ui_lang == "ru":
        return any(x in t for x in ["кто тебя сделал", "кто твой создатель", "кто создал", "кто создатель", "создатель"])
    return any(x in t for x in ["who made you", "who created you", "your creator", "your maker", "creator"])

# ====================== ОСНОВНОЙ ХЭНДЛЕР ======================
@safe_handler
async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.effective_chat:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    session = user_sessions.get(user_id)
    if not session:
        session = {"settings": {}, "history": [], "usage": {}}
        user_sessions[user_id] = session

    cfg = _get_cfg(session)

    # --- входной текст ---
    user_input = ""
    if update.message and update.message.text:
        user_input = update.message.text
    elif update.message and update.message.voice:
        # STT
        lang = VOICE_LANGS.get(cfg.interface_lang, "en-US")
        user_input = await speech_to_text_async(update, context, lang=lang)
    else:
        return

    user_input = user_input.strip()
    msg_norm = _norm_msg(user_input)

    # --- команды режима / переводчика ---
    if await _maybe_process_mode_commands(update, context, session, msg_norm, cfg):
        return
    if await _maybe_toggle_translator(update, context, session, msg_norm):
        return

    # --- триггеры переключения настроек (язык/уровень/стиль/режим) ---
    changed = False
    changed |= detect_language_switch(session, user_input)
    changed |= detect_level_switch(session, user_input)
    changed |= detect_style_switch(session, user_input)
    changed |= detect_mode_switch(session, user_input)

    if changed:
        cfg = _get_cfg(session)

    # --- rate limit ---
    await async_rate_limit(update, context, session, cfg.interface_lang)

    # --- быстрый "повтори последнее" (если надо) ---
    if msg_norm in {"/last", "last", "повтори", "повтори последнее"}:
        await _say_last_once(context, chat_id, session, cfg)
        return

    # ✅ Стикеры: ОТКЛЮЧАЕМ в режиме переводчика
    # стикеры (антифлуд и шанс внутри сервиса) — только в обычном чат-режиме
    if getattr(cfg, "task_mode", "chat") != "translator":
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

    # --- логика: переводчик vs чат ---
    if cfg.task_mode == "translator":
        out = await do_translate(
            user_input,
            interface_lang=cfg.interface_lang,
            target_lang=cfg.target_lang,
            direction=(session.get("translator") or {}).get("direction", "ui→target"),
            style=(session.get("translator") or {}).get("style", cfg.style),
            level=cfg.level,
            output="voice" if cfg.mode == "voice" else "text",
        )

        if cfg.mode == "voice":
            # TTS
            tts_lang = VOICE_LANGS.get(cfg.target_lang, VOICE_LANGS.get(cfg.interface_lang, "en-US"))
            await synthesize_voice_async(update, context, out, lang=tts_lang)
        else:
            await update.message.reply_text(out)
        session["last_reply_once"] = out
        return

    # --- обычный чат ---
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

    reply_text = await ask_gpt(messages, model="gpt-4o-mini", temperature=0.7, max_tokens=550)
    reply_text = (reply_text or "").strip()

    # сохраним историю
    append_history(session, "user", user_input, maxlen=MAX_HISTORY_LENGTH)
    append_history(session, "assistant", reply_text, maxlen=MAX_HISTORY_LENGTH)

    # запишем профиль (на всякий)
    try:
        save_user_profile(user_id, session.get("settings", {}))
    except Exception:
        logger.debug("save_user_profile failed", exc_info=True)

    # ответ
    if cfg.mode == "voice":
        lang = VOICE_LANGS.get(cfg.interface_lang, "en-US")
        await synthesize_voice_async(update, context, reply_text, lang=lang)
    else:
        await update.message.reply_text(reply_text, reply_markup=get_mode_keyboard(cfg.mode, cfg.interface_lang))

    session["last_reply_once"] = reply_text
