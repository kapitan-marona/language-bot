from __future__ import annotations
import asyncio
from typing import Literal, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from components.gpt_client import ask_gpt  # <— нужен для do_translate

Direction = Literal["ui→target", "target→ui"]
Output = Literal["text", "voice"]
TStyle = Literal["casual", "business"]

# Флажки и короткие ярлыки языков
FLAGS = {"ru":"🇷🇺","en":"🇬🇧","fr":"🇫🇷","es":"🇪🇸","de":"🇩🇪","sv":"🇸🇪","fi":"🇫🇮"}
SHORT = {"ru":"RU","en":"EN","fr":"FR","es":"ES","de":"DE","sv":"SV","fi":"FI"}

def flag(code: str) -> str:
    return FLAGS.get((code or "en").lower(), "🏳️")
def short(code: str) -> str:
    return SHORT.get((code or "en").lower(), (code or "EN").upper())

LANG_TITLES = {
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "fr": "🇫🇷 Français",
    "es": "🇪🇸 Español",
    "de": "🇩🇪 Deutsch",
    "sv": "🇸🇪 Svenska",
    "fi": "🇫🇮 Suomi",
}
def target_lang_title(code: str) -> str:
    return LANG_TITLES.get((code or "en").lower(), (code or "EN").upper())

# ——— Онбординг (обновлённый, лёгкий и блоками)
ONBOARDING = {
    "ru": [
        "🧩 Режим переводчика включён.",
        "Воспользуйся кнопками ниже, чтобы настроить переводчик:",
        "1) Направление — из языка интерфейса в целевой или наоборот.",
        "2) Формат — голос или текст.",
        "3) Стиль — разговорный или деловой.",
        "",
        "Метт переводит всё, что ты отправишь — без лишних обсуждений и вопросов. Готовый текст можно копировать, а аудио — сразу озвучено.",
        "Вернуться в обычный режим: /translator_off",
    ],
    "en": [
        "🧩 Translator mode is ON.",
        "Use the buttons below to tune the translator:",
        "1) Direction — from interface language to target or the other way around.",
        "2) Output — voice or text.",
        "3) Style — casual or business.",
        "",
        "Matt will translate everything you send — no extra chatter. Copy the text or use the ready voice.",
        "Back to chat mode: /translator_off",
    ],
}

def dir_compact_label(ui_code: str, direction: Direction, tgt_code: str) -> str:
    ui_flag, ui_short = flag(ui_code), short(ui_code)
    tg_flag, tg_short = flag(tgt_code), short(tgt_code)
    if direction == "ui→target":
        return f"{ui_flag} {ui_short} → {tg_flag} {tg_short}"
    return f"{tg_flag} {tg_short} → {ui_flag} {ui_short}"

def output_label(ui: str, output: Output) -> str:
    if ui == "ru":
        return "🎙 Голос" if output == "voice" else "✍️ Текст"
    return "🎙 Voice" if output == "voice" else "✍️ Text"

def style_label(ui: str, style: TStyle) -> str:
    if ui == "ru":
        return "😎 Разговорный" if style == "casual" else "🤓 Деловой"
    return "😎 Casual" if style == "casual" else "🤓 Business"

def translator_status_text(ui: str, tgt_title: str, cfg: Dict[str, Any]) -> str:
    parts = ONBOARDING["ru"] if ui == "ru" else ONBOARDING["en"]
    return "\n".join(parts)

def get_translator_keyboard(ui: str, cfg: Dict[str, Any], tgt_code: str) -> InlineKeyboardMarkup:
    btn_dir = InlineKeyboardButton(
        dir_compact_label(ui_code=ui, direction=cfg["direction"], tgt_code=tgt_code),
        callback_data="TR:TOGGLE:DIR"
    )
    btn_out = InlineKeyboardButton(
        output_label(ui, cfg["output"]),
        callback_data="TR:TOGGLE:OUT"
    )
    btn_style = InlineKeyboardButton(
        style_label(ui, cfg["style"]),
        callback_data="TR:TOGGLE:STYLE"
    )
    btn_exit = InlineKeyboardButton(
        "Выйти" if ui == "ru" else "Exit",
        callback_data="TR:EXIT"
    )
    return InlineKeyboardMarkup([
        [btn_dir],
        [btn_out, btn_style],
        [btn_exit],
    ])

# вставь РЯДОМ (до do_translate)
def _cap_for_level(level: str) -> str:
    lvl = (level or "A2").upper()
    if lvl == "A0": return "Keep it very simple. Max 1–2 short sentences."
    if lvl == "A1": return "Simple one-clause sentences. Max 1–3 sentences."
    if lvl == "A2": return "Clear basic grammar. Max 2–4 sentences."
    if lvl == "B1": return "Max 2–4 sentences."
    return "Max 2–5 sentences."  # B2–C2


def _translator_system(
    *,
    direction: Direction,
    style: TStyle,
    level: str,
    interface_lang: str,
    target_lang: str,
    voice: bool,
) -> str:
    d = "UI→TARGET" if (direction or "ui→target") == "ui→target" else "TARGET→UI"
    reg = "casual, idiomatic" if (style or "casual") == "casual" else "business, neutral, concise"
    caps = _cap_for_level(level)
    voice_hint = " Keep sentences short and well-paced for voice." if voice else ""
    return (
        "You are a precise translator.\n"
        f"Direction: {d}. Register: {reg}. {caps}{voice_hint}\n"
        "Return ONLY the translation. No comments, no templates, no follow-up question.\n"
        "No quotes or brackets. No emojis.\n"
        "Prefer established equivalents for idioms/proverbs; otherwise translate faithfully.\n"
        f"Source language is {'UI' if d=='UI→TARGET' else 'TARGET'}; "
        f"output language is {'TARGET' if d=='UI→TARGET' else 'UI'}."
    )

# ====== Строгий детерминированный перевод (экспорт для chat_handler) ======
async def do_translate(
    text: str,
    *,
    interface_lang: str,
    target_lang: str,
    direction: Direction,
    style: TStyle,
    level: str = "A2",
    output: Output = "text",       # "text" | "voice"
    timeout: float = 15.0,
) -> str:
    """
    Строгий и быстрый перевод: учитывает направление, стиль, уровень, формат (voice/text).
    Возвращает ТОЛЬКО перевод — без кавычек, скобок, эмодзи и пояснений.
    """
    if not text:
        return ""

    ui  = (interface_lang or "en").lower()
    tgt = (target_lang or "en").lower()

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

    async def _call():
        # мини-модель: быстрее и дешевле для переводов
        return await ask_gpt(messages, model="gpt-4o-mini", temperature=0.2, max_tokens=180)

    try:
        out = await asyncio.wait_for(_call(), timeout=timeout)
    except asyncio.TimeoutError:
        # мягкий фолбэк — вернём исходник, чтобы не «молчать»
        return text.strip()

    # подчистим кавычки/скобки/пробелы
    return (out or "").strip().strip("«»\"'()[] \n\r\t")
