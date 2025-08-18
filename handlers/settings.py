# handlers/settings.py
from __future__ import annotations
from typing import List, Tuple
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from components.profile_db import get_user_profile, save_user_profile
from components.promo import restrict_target_languages_if_needed, is_promo_valid
from components.i18n import get_ui_lang
from state.session import user_sessions
from handlers.chat.prompt_templates import INTRO_QUESTIONS, INTRO_QUESTIONS_EASY

logger = logging.getLogger(__name__)

# Языки (флаг + название)
LANGS: List[Tuple[str, str]] = [
    ("🇷🇺 Русский", "ru"),
    ("🇬🇧 English", "en"),
    ("🇫🇷 Français", "fr"),
    ("🇪🇸 Español", "es"),
    ("🇩🇪 Deutsch", "de"),
    ("🇸🇪 Svenska", "sv"),
    ("🇫🇮 Suomi", "fi"),
]

# Уровни — как в онбординге
LEVELS_ROW1 = ["A0", "A1", "A2"]
LEVELS_ROW2 = ["B1", "B2", "C1", "C2"]

# Два стиля общения
STYLES: List[Tuple[str, str]] = [
    ("😎 Разговорный", "casual"),
    ("🤓 Деловой", "business"),
]

# --- helpers (нейминг для UI) ---

def _name_for_lang(code: str) -> str:
    for title, c in LANGS:
        if c == code:
            return title
    return code

def _name_for_style(code: str) -> str:
    for title, c in STYLES:
        if c == code:
            return title
    return code

def _main_menu_text(ui: str, lang_name: str, level: str, style_name: str, english_only_note: bool) -> str:
    base_ru = (
        "⚙️ Настройки\n\n"
        f"• Язык: {lang_name}\n"
        f"• Уровень: {level}\n"
        f"• Стиль общения: {style_name}\n\n"
        "Что хочешь поменять?"
    )
    base_en = (
        "⚙️ Settings\n\n"
        f"• Language: {lang_name}\n"
        f"• Level: {level}\n"
        f"• Chat style: {style_name}\n\n"
        "What do you want to change?"
    )
    text = base_ru if ui == "ru" else base_en
    if english_only_note:
        text += ("\n\n❗ Промокод бессрочный, действует только для английского языка"
                 if ui == "ru" else
                 "\n\n❗ Promo is permanent and limits learning to English only")
    return text

def _menu_keyboard(ui: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Язык" if ui == "ru" else "Language", callback_data="SETTINGS:LANG"),
            InlineKeyboardButton("Уровень" if ui == "ru" else "Level", callback_data="SETTINGS:LEVEL"),
        ],
        [
            InlineKeyboardButton("Стиль" if ui == "ru" else "Style", callback_data="SETTINGS:STYLE"),
        ],
        [
            InlineKeyboardButton("▶️ Продолжить" if ui == "ru" else "▶️ Continue", callback_data="SETTINGS:APPLY"),
        ],
    ])

def _langs_keyboard(chat_id: int, ui: str) -> InlineKeyboardMarkup:
    prof = get_user_profile(chat_id) or {}
    lang_map = {code: title for title, code in LANGS}
    lang_map = restrict_target_languages_if_needed(prof, lang_map)

    items = [(title, code) for code, title in lang_map.items()]
    rows = []
    for i in range(0, len(items), 2):
        chunk = items[i:i+2]
        rows.append([InlineKeyboardButton(t, callback_data=f"SET:LANG:{c}") for (t, c) in chunk])

    rows.append([InlineKeyboardButton("👈 Назад" if ui == "ru" else "👈 Back", callback_data="SETTINGS:BACK")])
    return InlineKeyboardMarkup(rows)

def _levels_keyboard(ui: str) -> InlineKeyboardMarkup:
    row1 = [InlineKeyboardButton(x, callback_data=f"SET:LEVEL:{x}") for x in LEVELS_ROW1]
    row2 = [InlineKeyboardButton(x, callback_data=f"SET:LEVEL:{x}") for x in LEVELS_ROW2]
    back = [InlineKeyboardButton("👈 Назад" if ui == "ru" else "👈 Back", callback_data="SETTINGS:BACK")]
    return InlineKeyboardMarkup([row1, row2, back])

def _styles_keyboard(ui: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(title, callback_data=f"SET:STYLE:{code}")] for title, code in STYLES]
    rows.append([InlineKeyboardButton("👈 Назад" if ui == "ru" else "👈 Back", callback_data="SETTINGS:BACK")])
    return InlineKeyboardMarkup(rows)

# --- продолжение разговора после применения настроек ---

_BRIDGES = {
    # максимально простые, чтобы подходили для всех уровней
    "ru": ["Продолжаем!", "Давай продолжим.", "На чём остановились?", "Вернёмся к теме.", "Продолжим разговор."],
    "en": ["Let's continue!", "Shall we continue?", "Where did we stop?", "Back to the topic.", "Let's pick up the thread."],
    "fr": ["On continue !", "On reprend ?", "Où en était-on ?", "Revenons au sujet.", "On poursuit."],
    "es": ["¡Continuemos!", "¿Seguimos?", "¿Dónde nos quedamos?", "Volvamos al tema.", "Sigamos hablando."],
    "de": ["Weiter geht's!", "Machen wir weiter?", "Wo waren wir stehen geblieben?", "Zurück zum Thema.", "Lass uns fortfahren."],
    "sv": ["Vi fortsätter!", "Ska vi fortsätta?", "Var var vi?", "Tillbaka till ämnet.", "Låt oss fortsätta."],
    "fi": ["Jatketaan!", "Jatketaanko?", "Mihin jäimme?", "Takaisin aiheeseen.", "Jatketaan juttua."],
}

def _bridge_line(lang: str) -> str:
    return (_BRIDGES.get(lang) or _BRIDGES["en"])[0 if lang in ("ru","en") else 0]

def _find_last_assistant_question(sess: dict) -> str | None:
    """Берём последний вопрос ассистента из истории, чтобы не терять тему."""
    hist = sess.get("history") or []
    for m in reversed(hist):
        if not isinstance(m, dict) or m.get("role") != "assistant":
            continue
        text = (m.get("content") or "").strip()
        if not text:
            continue
        q = None
        # попробуем выделить последнее предложение с вопросительным знаком
        if "?" in text:
            parts = re.split(r'(?<=\?)', text)
            candidates = [p.strip() for p in parts if p.strip().endswith("?")]
            if candidates:
                q = candidates[-1]
        # если нет явного вопроса — возьмём последнюю строку
        if not q:
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            if lines:
                q = lines[-1]
        if q:
            if len(q) > 180:
                q = q[:177] + "…"
            return q
    return None

def _level_is_easy(level: str) -> bool:
    return (level or "").upper() in {"A0", "A1", "A2"}

# ---------- public handlers ----------

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ /settings — показать главное меню настроек. """
    ui = get_ui_lang(update, context)
    chat_id = update.effective_chat.id

    s = context.user_data or {}
    p = get_user_profile(chat_id) or {}

    language = p.get("target_lang") or s.get("language", "en")
    level = p.get("level") or s.get("level", "B1")
    style = p.get("style") or s.get("style", "casual")
    english_only_note = (p.get("promo_type") == "english_only" and is_promo_valid(p))

    text = _main_menu_text(ui, _name_for_lang(language), level, _name_for_style(style), english_only_note)

    q = getattr(update, "callback_query", None)
    if q and q.message:
        await q.edit_message_text(text, reply_markup=_menu_keyboard(ui))
        try:
            await q.answer()
        except Exception:
            pass
        return

    await context.bot.send_message(chat_id, text, reply_markup=_menu_keyboard(ui))

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback_data, начинающихся с SETTINGS:/SET:"""
    q = update.callback_query
    if not q or not q.data:
        return

    data = q.data
    ui = get_ui_lang(update, context)
    chat_id = q.message.chat.id

    if data == "SETTINGS:BACK":
        p = get_user_profile(chat_id) or {}
        s = context.user_data or {}
        language = p.get("target_lang") or s.get("language", "en")
        level = p.get("level") or s.get("level", "B1")
        style = p.get("style") or s.get("style", "casual")
        english_only_note = (p.get("promo_type") == "english_only" and is_promo_valid(p))
        await q.edit_message_text(
            _main_menu_text(ui, _name_for_lang(language), level, _name_for_style(style), english_only_note),
            reply_markup=_menu_keyboard(ui),
        )
        await q.answer()
        return

    if data == "SETTINGS:LANG":
        await q.edit_message_text(
            "Выбери язык:" if ui == "ru" else "Choose a language:",
            reply_markup=_langs_keyboard(chat_id, ui),
        )
        await q.answer()
        return

    if data == "SETTINGS:LEVEL":
        guide = None
        try:
            from components.onboarding import get_level_guide  # type: ignore
            guide = get_level_guide(ui)
        except Exception:
            guide = None
        text = ("Выбери уровень" if ui == "ru" else "Choose your level") + (f"\n\n{guide}" if guide else "")
        await q.edit_message_text(text, reply_markup=_levels_keyboard(ui))
        await q.answer()
        return

    if data == "SETTINGS:STYLE":
        await q.edit_message_text(
            "Выбери стиль общения:" if ui == "ru" else "Choose a chat style:",
            reply_markup=_styles_keyboard(ui),
        )
        await q.answer()
        return

    # --- Конкретные изменения: сохраняем и не отправляем «универсалку» ---
    if data.startswith("SET:LANG:"):
        code = data.split(":", 2)[-1]
        context.user_data["language"] = code
        save_user_profile(chat_id, target_lang=code)
        sess = user_sessions.setdefault(chat_id, {})
        sess["target_lang"] = code
        await q.answer("✅")
        p = get_user_profile(chat_id) or {}
        s = context.user_data or {}
        language = p.get("target_lang") or s.get("language", "en")
        level = p.get("level") or s.get("level", "B1")
        style = p.get("style") or s.get("style", "casual")
        english_only_note = (p.get("promo_type") == "english_only" and is_promo_valid(p))
        await q.edit_message_text(
            _main_menu_text(ui, _name_for_lang(language), level, _name_for_style(style), english_only_note),
            reply_markup=_menu_keyboard(ui),
        )
        return

    if data.startswith("SET:LEVEL:"):
        level = data.split(":", 2)[-1]
        context.user_data["level"] = level
        save_user_profile(chat_id, level=level)
        sess = user_sessions.setdefault(chat_id, {})
        sess["level"] = level
        await q.answer("✅")
        p = get_user_profile(chat_id) or {}
        s = context.user_data or {}
        language = p.get("target_lang") or s.get("language", "en")
        style = p.get("style") or s.get("style", "casual")
        english_only_note = (p.get("promo_type") == "english_only" and is_promo_valid(p))
        await q.edit_message_text(
            _main_menu_text(ui, _name_for_lang(language), level, _name_for_style(style), english_only_note),
            reply_markup=_menu_keyboard(ui),
        )
        return

    if data.startswith("SET:STYLE:"):
        style = data.split(":", 2)[-1]
        context.user_data["style"] = style
        save_user_profile(chat_id, style=style)
        sess = user_sessions.setdefault(chat_id, {})
        sess["style"] = style
        await q.answer("✅")
        p = get_user_profile(chat_id) or {}
        s = context.user_data or {}
        language = p.get("target_lang") or s.get("language", "en")
        level = p.get("level") or s.get("level", "B1")
        english_only_note = (p.get("promo_type") == "english_only" and is_promo_valid(p))
        await q.edit_message_text(
            _main_menu_text(ui, _name_for_lang(language), level, _name_for_style(style), english_only_note),
            reply_markup=_menu_keyboard(ui),
        )
        return

    # --- "Продолжить" — не сбрасываем тему, продолжаем от последнего вопроса ---
    if data == "SETTINGS:APPLY":
        p = get_user_profile(chat_id) or {}
        s = context.user_data or {}
        new_lang = p.get("target_lang") or s.get("language", "en")
        new_level = p.get("level") or s.get("level", "B1")
        new_style = p.get("style") or s.get("style", "casual")

        sess = user_sessions.setdefault(chat_id, {})
        if new_lang:  sess["target_lang"] = new_lang
        if new_level: sess["level"] = new_level
        if new_style: sess["style"] = new_style

        try:
            await q.answer("▶️")
        except Exception:
            pass

        confirm = (
            f"✅ Настройки применены.\nЯзык: {_name_for_lang(new_lang)} • Уровень: {new_level} • Стиль: {_name_for_style(new_style)}"
            if ui == "ru" else
            f"✅ Settings applied.\nLanguage: {_name_for_lang(new_lang)} • Level: {new_level} • Style: {_name_for_style(new_style)}"
        )
        await context.bot.send_message(chat_id, confirm)

        # 1) Пытаемся продолжить предыдущую тему (берём последний вопрос ассистента)
        last_q = _find_last_assistant_question(sess)

        # 2) Если нет — берём уровневую «первую реплику»
        if not last_q:
            if _level_is_easy(new_level):
                pool = INTRO_QUESTIONS_EASY.get(new_lang, INTRO_QUESTIONS_EASY.get("en", ["Hi! How are you today?"]))
            else:
                pool = INTRO_QUESTIONS.get(new_lang, INTRO_QUESTIONS.get("en", ["What’s up?"]))
            line = pool[0] if not isinstance(pool, list) else (pool[0] if not pool else pool[0])
            # чуть рандома: если это список, выберем случайный
            if isinstance(pool, list) and pool:
                import random
                line = random.choice(pool)
            msg = line
        else:
            # короткий мостик + предыдущий вопрос — в ЦЕЛЕВОМ языке
            bridge = _bridge_line(new_lang)
            msg = f"{bridge} {last_q}"

        await context.bot.send_message(chat_id, msg)

        # Запишем в историю как реплику ассистента — чтобы GPT «помнил» этот ход
        hist = sess.setdefault("history", [])
        hist.append({"role": "assistant", "content": msg})
        return
