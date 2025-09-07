# components/translator.py
from __future__ import annotations
from typing import Literal, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

Direction = Literal["ui→target", "target→ui"]
Output = Literal["text", "voice"]
TStyle = Literal["casual", "business"]

ONBOARDING = {
    "ru": [
        "🟢 Режим переводчика включён.",
        "Метт переводит всё, что вы отправляете. Пишите только текст для перевода.",
        "Для вопросов и обсуждений вернитесь в обычный режим: /translator off.",
    ],
    "en": [
        "🟢 Translator mode is ON.",
        "Matt translates everything you send. Send only the text to be translated.",
        "For questions or discussion, switch back to chat: /translator off.",
    ],
}

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

def _dir_label(ui: str, direction: Direction, tgt_title: str) -> str:
    arrow = f"UI → {tgt_title}" if direction == "ui→target" else f"{tgt_title} → UI"
    return ("Направление: " if ui == "ru" else "Direction: ") + arrow

def _out_label(ui: str, output: Output) -> str:
    d = {"text": "Текст", "voice": "Голос"} if ui == "ru" else {"text": "Text", "voice": "Voice"}
    return ("Формат: " if ui == "ru" else "Output: ") + d[output]

def _style_label(ui: str, style: TStyle) -> str:
    if ui == "ru":
        return "Стиль: 😎 Разговорный" if style == "casual" else "Стиль: 🤓 Деловой"
    return "Style: 😎 Casual" if style == "casual" else "Style: 🤓 Business"

def translator_status_text(ui: str, tgt_title: str, cfg: Dict[str, Any]) -> str:
    parts = ONBOARDING["ru"] if ui == "ru" else ONBOARDING["en"]
    info = "\n".join(parts)
    meta = f"\n\n{_dir_label(ui, cfg['direction'], tgt_title)} • {_out_label(ui, cfg['output'])} • {_style_label(ui, cfg['style'])}"
    return info + meta

def get_translator_keyboard(ui: str, cfg: Dict[str, Any], tgt_title: str) -> InlineKeyboardMarkup:
    btn_dir = InlineKeyboardButton(
        f"🔁 {_dir_label(ui, cfg['direction'], tgt_title)}",
        callback_data="TR:TOGGLE:DIR"
    )
    btn_out = InlineKeyboardButton(
        f"🎙 {_out_label(ui, cfg['output'])}",
        callback_data="TR:TOGGLE:OUT"
    )
    btn_style = InlineKeyboardButton(
        f"🎚 {_style_label(ui, cfg['style'])}",
        callback_data="TR:TOGGLE:STYLE"
    )
    btn_exit = InlineKeyboardButton(
        "🚪 Выйти из переводчика" if ui == "ru" else "🚪 Exit translator",
        callback_data="TR:EXIT"
    )
    return InlineKeyboardMarkup([
        [btn_dir],
        [btn_out, btn_style],
        [btn_exit],
    ])
