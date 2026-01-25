# components/translator.py
from __future__ import annotations

import asyncio
import logging
from typing import Literal, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from components.gpt_client import ask_gpt  # нужен для do_translate

logger = logging.getLogger(__name__)

Direction = Literal["ui→target", "target→ui"]
Output = Literal["text", "voice"]
TStyle = Literal["casual", "business"]

# Флажки и короткие ярлыки языков
FLAGS = {"ru": "🇷🇺", "en": "🇬🇧", "fr": "🇫🇷", "es": "🇪🇸", "de": "🇩🇪", "sv": "🇸🇪", "fi": "🇫🇮"}
SHORT = {"ru": "RU", "en": "EN", "fr": "FR", "es": "ES", "de": "DE", "sv": "SV", "fi": "FI"}

LANG_TITLES = {
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "fr": "🇫🇷 Français",
    "es": "🇪🇸 Español",
    "de": "🇩🇪 Deutsch",
    "sv": "🇸🇪 Svenska",
    "fi": "🇫🇮 Suomi",
}

# Человекочитаемые названия (для системки)
LANG_NAMES = {
    "ru": "Russian",
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "sv": "Swedish",
    "fi": "Finnish",
}

def flag(code: str) -> str:
    return FLAGS.get((code or "en").lower(), "🏳️")

def short(code: str) -> str:
    return SHORT.get((code or "en").lower(), (code or "EN").upper())

def target_lang_title(code: str) -> str:
    return LANG_TITLES.get((code or "en").lower(), (code or "EN").upper())

# ——— Текст-инструкция для переводчика (без примеров про "почки")
ONBOARDING = {
    "ru": [
        "🧩 Режим переводчика включён.",
        "Я не веду диалог — я перевожу то, что ты отправляешь.",
        "Если ты уточняешь смысл (например, добавляешь пояснение в скобках) — я учту это при переводе.",
        "",
        "⬅️ Вернуться в обычный режим: /translator_off",
        "🔁 Направление перевода можно менять кнопкой ниже.",
    ],
    "en": [
        "🧩 Translator mode is ON.",
        "I don’t chat here — I translate what you send.",
        "If you add a clarification (e.g., in parentheses), I’ll use it to choose the right meaning.",
        "",
        "⬅️ Back to chat mode: /translator_off",
        "🔁 You can toggle direction with the button below.",
    ],
}

def dir_compact_label(ui_code: str, direction: Direction, tgt_code: str) -> str:
    ui_flag, ui_short = flag(ui_code), short(ui_code)
    tg_flag, tg_short = flag(tgt_code), short(tgt_code)
    if direction == "ui→target":
        return f"{ui_flag} {ui_short} → {tg_flag} {tg_short}"
    return f"{tg_flag} {tg_short} → {ui_flag} {ui_short}"

def translator_status_text(ui: str, tgt_title: str, cfg: Dict[str, Any]) -> str:
    parts = ONBOARDING["ru"] if ui == "ru" else ONBOARDING["en"]
    return "\n".join(parts)

def get_translator_keyboard(ui: str, cfg: Dict[str, Any], tgt_code: str) -> InlineKeyboardMarkup:
    # ✅ Оставляем только одну кнопку: направление
    btn_dir = InlineKeyboardButton(
        dir_compact_label(ui_code=ui, direction=cfg["direction"], tgt_code=tgt_code),
        callback_data="TR:TOGGLE:DIR",
    )
    return InlineKeyboardMarkup([[btn_dir]])

# === Вспомогательное: «сжатие» по уровню ===
def _cap_for_level(level: str) -> str:
    lvl = (level or "A2").upper()
    if lvl == "A0":
        return "Keep it very simple. Max 1–2 short sentences."
    if lvl == "A1":
        return "Simple one-clause sentences. Max 1–3 sentences."
    if lvl == "A2":
        return "Clear basic grammar. Max 2–4 sentences."
    if lvl == "B1":
        return "Max 2–4 sentences."
    return "Max 2–5 sentences."  # B2–C2

def _lang_name(code: str) -> str:
    c = (code or "en").lower()
    return LANG_NAMES.get(c, c.upper())

def _translator_system(
    *,
    direction: Direction,
    style: TStyle,
    level: str,
    interface_lang: str,
    target_lang: str,
    voice: bool,
) -> str:
    """
    Жёстко фиксируем языки, чтобы модель не уезжала в английский по умолчанию.
    """
    d = "UI→TARGET" if (direction or "ui→target") == "ui→target" else "TARGET→UI"
    reg = "casual, idiomatic" if (style or "casual") == "casual" else "business, neutral, concise"
    caps = _cap_for_level(level)
    voice_hint = " Keep sentences short and well-paced for voice." if voice else ""

    src_code = interface_lang if d == "UI→TARGET" else target_lang
    dst_code = target_lang if d == "UI→TARGET" else interface_lang
    src_name = _lang_name(src_code)
    dst_name = _lang_name(dst_code)

    dst_guard = (
        f"Output MUST be in {dst_name} only. "
        f"Do NOT use English unless {dst_name} is English."
    )


    return (
        "You are a precise bilingual translator.\n"
        f"Direction: {d}. Register: {reg}. {caps}{voice_hint}\n"
        f"Source language: {src_name} (code: {src_code.upper()}).\n"
        f"Target language: {dst_name} (code: {dst_code.upper()}).\n"
        f"{dst_guard}\n"

        "You are a translation engine, not a chat assistant.\n"
        "Never answer the user. Never add comments. Never ask questions.\n\n"

        "Assume the user input is ALWAYS written in the Source language unless explicitly stated otherwise.\n\n"

        "Output ONLY the translation in the Target language.\n"
        "Do NOT include any words in the Source language.\n"

        "Return ONLY the translation — no comments, no templates, no follow-up question.\n"
        "No quotes/brackets. No emojis.\n"
        "Prefer established equivalents for idioms/proverbs; otherwise translate faithfully."
    )


# ====== Строгий перевод (экспорт для chat_handler) ======
async def do_translate(
    text: str,
    *,
    interface_lang: str,
    target_lang: str,
    direction: Direction,
    style: TStyle,
    level: str = "A2",
    output: Output = "text",  # "text" | "voice"
    timeout: float = 15.0,
) -> str:
    """
    Строгий и быстрый перевод: учитывает направление, стиль, уровень, формат (voice/text).
    Возвращает ТОЛЬКО перевод — без кавычек, скобок, эмодзи и пояснений.
    """
    if not text:
        return ""

    ui = (interface_lang or "en").lower()
    tgt = (target_lang or "en").lower()

    import re

    # Если пользователь ввёл "переведи ..." / "translate ..." — берём текст после ключевых слов
    pattern = r"(?:(?:translate|переведи|как будет|что значит|meaning of)\s*[:,\-–]?\s*)[\"“”']?(.*?)[\"“”']?$"
    m = re.search(pattern, text.strip(), re.IGNORECASE)
    if m and len(m.group(1)) > 1:
        text = m.group(1).strip()

    # Если текст выглядит как вопрос — заставляем перевести вопрос, а не отвечать
    if re.match(r"^(what|how|can|is|are|do|does|did|where|who|when|why)\b", text.lower()):
        text = f"Translate this question only, do not answer it: {text}"

    sys = _translator_system(
        direction=direction,
        style=style,
        level=level,
        interface_lang=ui,
        target_lang=tgt,
        voice=(output == "voice"),
    )

    messages = [
        {"role": "system", "content": sys},
        {"role": "user", "content": text},
    ]

    logger.debug(
        "[TR] call: dir=%s style=%s lvl=%s out=%s ui=%s tgt=%s text_len=%d",
        direction, style, level, output, ui, tgt, len(text or "")
    )

    async def _call():
        return await ask_gpt(messages, model="gpt-4o-mini", temperature=0.2, max_tokens=180)

    try:
        out = await asyncio.wait_for(_call(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error("[TR] do_translate timeout")
        return text.strip()
    except TypeError as e:
        # если ask_gpt в твоей версии без именованных параметров — подстрахуемся
        logger.error("[TR] do_translate error (TypeError): %s", e)
        out = await ask_gpt(messages, model="gpt-4o-mini")

    result = (out or "").strip().strip("«»\"'()[] \n\r\t")
    return result
