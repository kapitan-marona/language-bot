# components/translator.py
from __future__ import annotations

import logging
from typing import Dict, Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


def target_lang_title(code: str) -> str:
    code = (code or "").lower()
    titles = {
        "ru": "Russian",
        "en": "English",
        "fr": "Français",
        "es": "Español",
        "de": "Deutsch",
        "sv": "Svenska",
        "fi": "Suomi",
    }
    return titles.get(code, code)


def translator_status_text(ui: str, tgt_title: str, cfg: Dict[str, Any]) -> str:
    """
    Инструкция к переводчику: без дублирования настроек (всё в /settings).
    """
    direction = (cfg.get("direction") or "ui→target").strip()
    if direction not in ("ui→target", "target→ui"):
        direction = "ui→target"

    if ui == "ru":
        dir_line = (
            "Направление: с твоего языка → на язык обучения"
            if direction == "ui→target"
            else "Направление: с языка обучения → на твой язык"
        )
        return (
            "🧩 <b>Режим переводчика включён.</b>\n\n"
            f"{dir_line}\n\n"
            "Я <b>не веду диалог</b> — я только перевожу то, что ты пишешь.\n"
            "Если ты добавляешь уточнение в скобках, я учитываю контекст.\n\n"
            "Настройки (язык/уровень/стиль/формат) меняются в <b>/settings</b>.\n"
            "Выйти из переводчика: <b>/chat</b> или <b>/translator_off</b>."
        )

    dir_line = (
        "Direction: your UI language → learning language"
        if direction == "ui→target"
        else "Direction: learning language → your UI language"
    )
    return (
        "🧩 <b>Translator mode is ON.</b>\n\n"
        f"{dir_line}\n\n"
        "I <b>don’t chat</b> — I only translate what you write.\n"
        "If you add a short hint in parentheses, I use it as context.\n\n"
        "Settings (language/level/style/format) are in <b>/settings</b>.\n"
        "Exit translator: <b>/chat</b> or <b>/translator_off</b>."
    )


def get_translator_keyboard(ui: str, cfg: Dict[str, Any], tgt_code: str) -> InlineKeyboardMarkup:
    """
    Оставляем ОДНУ кнопку: направление перевода.
    Все остальные настройки — через /settings.
    """
    direction = (cfg.get("direction") or "ui→target").strip()
    if direction not in ("ui→target", "target→ui"):
        direction = "ui→target"

    if ui == "ru":
        label = "➡️ RU → target" if direction == "ui→target" else "⬅️ target → RU"
    else:
        label = "➡️ UI → target" if direction == "ui→target" else "⬅️ target → UI"

    btn_dir = InlineKeyboardButton(label, callback_data="TR:TOGGLE:DIR")
    return InlineKeyboardMarkup([[btn_dir]])
