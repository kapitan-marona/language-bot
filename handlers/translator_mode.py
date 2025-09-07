# translator_mode.py
from __future__ import annotations
from typing import Dict, Any
import re
from telegram import Update
from telegram.ext import ContextTypes

from state.session import user_sessions
from components.translator import (
    get_translator_keyboard,
    translator_status_text,
    target_lang_title,
)

TRANSLATE_TRIGGERS = (
    r"^\s*/translate\b",
    r"^\s*/перевод\b",
    r"\b(переведи|перевод|как сказать|как будет)\b",
    r"\b(translate|how to say|what('?s| is) .* in)\b",
)

def detect_translation_intent(text: str) -> bool:
    t = (text or "").lower()
    return any(re.search(p, t) for p in TRANSLATE_TRIGGERS)

def ensure_tr_defaults(sess: Dict[str, Any]) -> None:
    tr = sess.setdefault("translator", {})
    tr.setdefault("direction", "ui→target")  # "ui→target" | "target→ui"
    tr.setdefault("output", "text")          # "text" | "voice"
    tr.setdefault("style", "casual")         # "casual" | "business"

async def enter_translator(update: Update, context: ContextTypes.DEFAULT_TYPE, sess: Dict[str, Any]):
    sess["task_mode"] = "translator"
    ensure_tr_defaults(sess)

    ui = sess.get("interface_lang", "ru")
    tgt_code = (sess.get("target_lang") or "en").lower()
    txt = translator_status_text(ui, target_lang_title(tgt_code), sess["translator"])
    kb = get_translator_keyboard(ui, sess["translator"], target_lang_title(tgt_code))
    await context.bot.send_message(update.effective_chat.id, txt, reply_markup=kb)

async def exit_translator(update: Update, context: ContextTypes.DEFAULT_TYPE, sess: Dict[str, Any]):
    ui = sess.get("interface_lang", "ru")
    sess["task_mode"] = "chat"
    sess["just_left_translator"] = True  # разовый wrap-up
    await context.bot.send_message(
        update.effective_chat.id,
        "↩️ Режим переводчика выключен." if ui == "ru" else "↩️ Translator mode is OFF."
    )

async def handle_translator_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    sess = user_sessions.setdefault(chat_id, {})
    ensure_tr_defaults(sess)

    ui = sess.get("interface_lang", "ru")
    tgt_code = (sess.get("target_lang") or "en").lower()
    cfg = sess["translator"]
    data = (query.data or "")

    if data == "TR:TOGGLE:DIR":
        cfg["direction"] = "target→ui" if cfg["direction"] == "ui→target" else "ui→target"
    elif data == "TR:TOGGLE:OUT":
        cfg["output"] = "voice" if cfg["output"] == "text" else "text"
    elif data == "TR:TOGGLE:STYLE":
        cfg["style"] = "business" if cfg["style"] == "casual" else "casual"
    elif data == "TR:EXIT":
        sess["task_mode"] = "chat"
        sess["just_left_translator"] = True
        await query.edit_message_text("↩️ Режим переводчика выключен." if ui == "ru" else "↩️ Translator mode is OFF.")
        return

    txt = translator_status_text(ui, target_lang_title(tgt_code), cfg)
    kb = get_translator_keyboard(ui, cfg, target_lang_title(tgt_code))
    await query.edit_message_text(txt, reply_markup=kb)
