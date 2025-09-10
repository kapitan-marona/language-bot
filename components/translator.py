# components/translator.py
from __future__ import annotations
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

# ====== Строгий детерминированный перевод (экспорт для chat_handler) ======
async def do_translate(
    text: str,
    *,
    interface_lang: str,
    target_lang: str,
    direction: Direction,
    style: TStyle,
) -> str:
    """
    Только перевод, без кавычек/эмодзи/пояснений.
    Учитывает направление и стиль (casual/business).
    """
    if not text:
        return ""

    src_lang = interface_lang if direction == "ui→target" else target_lang
    dst_lang = target_lang if direction == "ui→target" else interface_lang

    sys = (
        "You are a precise bilingual translator. "
        f"Translate from {src_lang.upper()} to {dst_lang.upper()} in a {style} tone. "
        "Output ONLY the translation. No quotes. No brackets. No explanations. No emojis."
    )
    prompt = [
        {"role": "system", "content": sys},
        {"role": "user", "content": text},
    ]
    out = await ask_gpt(prompt, "gpt-4o-mini")
    return (out or "").strip().strip("«»\"' ")
