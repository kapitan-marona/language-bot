# handlers/settings.py
from __future__ import annotations

import logging
from typing import Dict, Any, List, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from components.profile_db import get_user_profile, save_user_profile
from components.promo import restrict_target_languages_if_needed, is_promo_valid
from components.i18n import get_ui_lang
from state.session import user_sessions

logger = logging.getLogger(__name__)

# -------------------- справочники --------------------

LANGS: List[Tuple[str, str]] = [
    ("🇷🇺 Русский", "ru"),
    ("🇬🇧 English", "en"),
    ("🇫🇷 Français", "fr"),
    ("🇪🇸 Español", "es"),
    ("🇩🇪 Deutsch", "de"),
    ("🇸🇪 Svenska", "sv"),
    ("🇫🇮 Suomi", "fi"),
]

LEVELS_ROW1 = ["A0", "A1", "A2"]
LEVELS_ROW2 = ["B1", "B2", "C1", "C2"]

STYLE_TITLES = {
    "casual": {"ru": "😎 Разговорный", "en": "😎 Casual"},
    "business": {"ru": "🤓 Деловой", "en": "🤓 Business"},
}
STYLE_ORDER = ["casual", "business"]

# iOS-подобный индикатор выбранного пункта (одинаковая ширина)
DOT_ON = "●"
DOT_OFF = "○"

# -------------------- helpers --------------------

def _name_for_lang(code: str) -> str:
    for title, c in LANGS:
        if c == code:
            return title
    return (code or "").upper() or "EN"

def _name_for_style(code: str, ui: str) -> str:
    d = STYLE_TITLES.get(code, {})
    return d.get(ui, d.get("ru", code))

def _state_from(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Dict[str, Any]:
    ui = get_ui_lang(update, context)
    chat_id = update.effective_chat.id

    prof = get_user_profile(chat_id) or {}
    sess = user_sessions.setdefault(chat_id, {})

    target_lang = prof.get("target_lang") or sess.get("target_lang") or "en"
    level = prof.get("level") or sess.get("level") or "B1"
    style = prof.get("style") or sess.get("style") or "casual"

    out_mode = sess.get("mode") or "text"  # text | voice

    append_tr = False
    if (level or "").upper() in ("A0", "A1"):
        append_tr = bool(prof.get("append_translation"))

    english_only_note = (prof.get("promo_type") == "english_only" and is_promo_valid(prof))

    return {
        "ui": ui,
        "chat_id": chat_id,
        "prof": prof,
        "sess": sess,
        "target_lang": target_lang,
        "level": level,
        "style": style,
        "out_mode": out_mode,
        "append_tr": append_tr,
        "english_only_note": english_only_note,
    }

def _main_text(
    ui: str,
    lang_name: str,
    level: str,
    style_name: str,
    out_mode: str,
    append_tr: bool,
    english_only_note: bool,
) -> str:
    out_title = ("🔊 Аудио" if ui == "ru" else "🔊 Voice") if out_mode == "voice" else ("⌨️ Текст" if ui == "ru" else "⌨️ Text")

    if ui == "ru":
        text = (
            "⚙️ Настройки\n\n"
            f"Выбранный язык: {lang_name}\n"
            f"Установленный уровень: {level}\n"
            f"Стиль: {style_name}\n"
            f"Формат ответа Мэтта: {out_title}\n"
            f"Дублирование: {'Вкл' if append_tr else 'Выкл'}\n\n"
            "Выбери, что поменять ↓"
        )
        if english_only_note:
            text += "\n\n❗ Промокод бессрочный, действует только для английского языка"
        return text

    text = (
        "⚙️ Settings\n\n"
        f"Language: {lang_name}\n"
        f"Level: {level}\n"
        f"Style: {style_name}\n"
        f"Matt's output: {out_title}\n"
        f"Native hints: {'On' if append_tr else 'Off'}\n\n"
        "Choose what to change ↓"
    )
    if english_only_note:
        text += "\n\n❗ Promo is permanent and limits learning to English only"
    return text

def _pill(label: str, active: bool) -> str:
    return f"{DOT_ON if active else DOT_OFF} {label}"

def _kb_main(ui: str, out_mode: str) -> InlineKeyboardMarkup:
    # 1 строка: Текст / Аудио
    b_text = _pill("⌨️ Текст" if ui == "ru" else "⌨️ Text", out_mode == "text")
    b_voice = _pill("🔊 Аудио" if ui == "ru" else "🔊 Voice", out_mode == "voice")

    # 2 строка: Настройки / Premium
    # 3 строка: Готово
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(b_text, callback_data="S:FORMAT:text"),
            InlineKeyboardButton(b_voice, callback_data="S:FORMAT:voice"),
        ],
        [
            InlineKeyboardButton("🛠 Настройки" if ui == "ru" else "🛠 Settings", callback_data="S:OPEN:SETTINGS"),
            InlineKeyboardButton("⭐ Premium", callback_data="S:OPEN:PREMIUM"),
        ],
        [
            InlineKeyboardButton("✅ Готово" if ui == "ru" else "✅ Done", callback_data="S:DONE"),
        ],
    ])

def _kb_settings(ui: str, append_tr: bool) -> InlineKeyboardMarkup:
    dup = ("Дублирование: Вкл" if ui == "ru" else "Native: On") if append_tr else ("Дублирование: Выкл" if ui == "ru" else "Native: Off")
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Язык" if ui == "ru" else "Language", callback_data="S:OPEN:LANG"),
            InlineKeyboardButton("Уровень" if ui == "ru" else "Level", callback_data="S:OPEN:LEVEL"),
        ],
        [
            InlineKeyboardButton("Стиль" if ui == "ru" else "Style", callback_data="S:OPEN:STYLE"),
            InlineKeyboardButton(dup, callback_data="S:TOGGLE:APPEND_TR"),
        ],
        [
            InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:BACK:MAIN"),
            InlineKeyboardButton("✅ Готово" if ui == "ru" else "✅ Done", callback_data="S:DONE"),
        ],
    ])

def _langs_keyboard(chat_id: int, ui: str) -> InlineKeyboardMarkup:
    prof = get_user_profile(chat_id) or {}
    lang_map = {code: title for title, code in LANGS}
    lang_map = restrict_target_languages_if_needed(prof, lang_map)

    items = [(title, code) for code, title in lang_map.items()]
    rows = []
    for i in range(0, len(items), 2):
        chunk = items[i:i + 2]
        rows.append([InlineKeyboardButton(t, callback_data=f"S:SET:LANG:{c}") for (t, c) in chunk])

    rows.append([InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:BACK:SETTINGS")])
    return InlineKeyboardMarkup(rows)

def _levels_keyboard(ui: str) -> InlineKeyboardMarkup:
    row1 = [InlineKeyboardButton(x, callback_data=f"S:SET:LEVEL:{x}") for x in LEVELS_ROW1]
    row2 = [InlineKeyboardButton(x, callback_data=f"S:SET:LEVEL:{x}") for x in LEVELS_ROW2]
    extra = [InlineKeyboardButton("ℹ️ Гайд по уровням" if ui == "ru" else "ℹ️ Level guide", callback_data="S:OPEN:LEVEL_GUIDE")]
    back = [InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:BACK:SETTINGS")]
    return InlineKeyboardMarkup([row1, row2, extra, back])

def _styles_keyboard(ui: str) -> InlineKeyboardMarkup:
    rows = []
    for code in STYLE_ORDER:
        rows.append([InlineKeyboardButton(_name_for_style(code, ui), callback_data=f"S:SET:STYLE:{code}")])
    rows.append([InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:BACK:SETTINGS")])
    return InlineKeyboardMarkup(rows)

async def _edit_or_send(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, kb: InlineKeyboardMarkup | None):
    q = getattr(update, "callback_query", None)
    if q and q.message:
        await q.edit_message_text(text, reply_markup=kb)
        return
    await context.bot.send_message(update.effective_chat.id, text, reply_markup=kb)

async def _hide_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = getattr(update, "callback_query", None)
    if q and q.message:
        try:
            # прячем клавиатуру, сообщение остаётся
            await q.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

# -------------------- команды-алиасы (не открывают меню) --------------------

async def cmd_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    sess["mode"] = "voice"
    ui = get_ui_lang(update, context)
    await update.effective_message.reply_text("🔊 Теперь отвечаю голосом." if ui == "ru" else "🔊 Now I'll reply with voice.")

async def cmd_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    sess["mode"] = "text"
    ui = get_ui_lang(update, context)
    await update.effective_message.reply_text("⌨️ Теперь отвечаю текстом." if ui == "ru" else "⌨️ Now I'll reply with text.")

# -------------------- публичные хендлеры --------------------

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    st = _state_from(update, context)
    ui = st["ui"]
    text = _main_text(
        ui=ui,
        lang_name=_name_for_lang(st["target_lang"]),
        level=st["level"],
        style_name=_name_for_style(st["style"], ui),
        out_mode=st["out_mode"],
        append_tr=st["append_tr"],
        english_only_note=st["english_only_note"],
    )
    await _edit_or_send(update, context, text, _kb_main(ui, st["out_mode"]))

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.data:
        return

    data = q.data
    st = _state_from(update, context)
    ui: str = st["ui"]
    chat_id: int = st["chat_id"]
    sess: Dict[str, Any] = st["sess"]
    prof: Dict[str, Any] = st["prof"]

    try:
        await q.answer()
    except Exception:
        pass

    # DONE: просто спрятать клавиатуру
    if data == "S:DONE":
        await _hide_menu(update, context)
        return

    # Навигация
    if data == "S:OPEN:SETTINGS":
        level_now = (prof.get("level") or sess.get("level") or "B1").upper()
        append_tr = bool(prof.get("append_translation")) if level_now in ("A0", "A1") else False

        text = _main_text(
            ui=ui,
            lang_name=_name_for_lang(prof.get("target_lang") or sess.get("target_lang") or "en"),
            level=prof.get("level") or sess.get("level") or "B1",
            style_name=_name_for_style(prof.get("style") or sess.get("style") or "casual", ui),
            out_mode=sess.get("mode") or "text",
            append_tr=append_tr,
            english_only_note=(prof.get("promo_type") == "english_only" and is_promo_valid(prof)),
        )
        await q.edit_message_text(text, reply_markup=_kb_settings(ui, append_tr))
        return

    if data == "S:BACK:MAIN":
        await cmd_settings(update, context)
        return

    if data == "S:BACK:SETTINGS":
        level_now = (prof.get("level") or sess.get("level") or "B1").upper()
        append_tr = bool(prof.get("append_translation")) if level_now in ("A0", "A1") else False

        text = _main_text(
            ui=ui,
            lang_name=_name_for_lang(prof.get("target_lang") or sess.get("target_lang") or "en"),
            level=prof.get("level") or sess.get("level") or "B1",
            style_name=_name_for_style(prof.get("style") or sess.get("style") or "casual", ui),
            out_mode=sess.get("mode") or "text",
            append_tr=append_tr,
            english_only_note=(prof.get("promo_type") == "english_only" and is_promo_valid(prof)),
        )
        await q.edit_message_text(text, reply_markup=_kb_settings(ui, append_tr))
        return

    # Подменю: Язык / Уровень / Стиль
    if data == "S:OPEN:LANG":
        await q.edit_message_text(
            "Выбери язык:" if ui == "ru" else "Choose a language:",
            reply_markup=_langs_keyboard(chat_id, ui),
        )
        return

    if data == "S:OPEN:LEVEL":
        await q.edit_message_text(
            "Выбери уровень:" if ui == "ru" else "Choose your level:",
            reply_markup=_levels_keyboard(ui),
        )
        return

    if data == "S:OPEN:LEVEL_GUIDE":
        guide = None
        try:
            from components.onboarding import get_level_guide  # type: ignore
            guide = get_level_guide(ui)
        except Exception:
            guide = None

        if not guide:
            guide = (
                "A0–A1: очень просто\nA2: базово\nB1: средне\nB2+: свободнее"
                if ui == "ru"
                else
                "A0–A1: very simple\nA2: basic\nB1: intermediate\nB2+: advanced"
            )

        await q.edit_message_text(
            guide,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:OPEN:LEVEL")]
            ]),
        )
        return

    if data == "S:OPEN:STYLE":
        await q.edit_message_text(
            "Выбери стиль:" if ui == "ru" else "Choose a style:",
            reply_markup=_styles_keyboard(ui),
        )
        return

    # Тумблер дублирования (только A0–A1)
    if data == "S:TOGGLE:APPEND_TR":
        level_now = (prof.get("level") or sess.get("level") or "B1").upper()
        if level_now not in ("A0", "A1"):
            try:
                await q.answer("Недоступно" if ui == "ru" else "Unavailable", show_alert=True)
            except Exception:
                pass
            return

        new_val = not bool(prof.get("append_translation"))
        try:
            save_user_profile(chat_id, append_translation=new_val, append_translation_lang=(prof.get("interface_lang") or "en"))
        except Exception:
            logger.exception("Failed to toggle append_translation")

        prof = get_user_profile(chat_id) or prof
        append_tr = bool(prof.get("append_translation"))

        text = _main_text(
            ui=ui,
            lang_name=_name_for_lang(prof.get("target_lang") or sess.get("target_lang") or "en"),
            level=prof.get("level") or sess.get("level") or "B1",
            style_name=_name_for_style(prof.get("style") or sess.get("style") or "casual", ui),
            out_mode=sess.get("mode") or "text",
            append_tr=append_tr,
            english_only_note=(prof.get("promo_type") == "english_only" and is_promo_valid(prof)),
        )
        await q.edit_message_text(text, reply_markup=_kb_settings(ui, append_tr))
        return

    # Формат ответа (text/voice) — перерисуем ГЛАВНОЕ меню с ●/○
    if data.startswith("S:FORMAT:"):
        val = data.split(":", 2)[-1]
        sess["mode"] = "voice" if val == "voice" else "text"

        level_now = (prof.get("level") or sess.get("level") or "B1").upper()
        append_tr = bool(prof.get("append_translation")) if level_now in ("A0", "A1") else False

        text = _main_text(
            ui=ui,
            lang_name=_name_for_lang(prof.get("target_lang") or sess.get("target_lang") or "en"),
            level=prof.get("level") or sess.get("level") or "B1",
            style_name=_name_for_style(prof.get("style") or sess.get("style") or "casual", ui),
            out_mode=sess["mode"],
            append_tr=append_tr,
            english_only_note=(prof.get("promo_type") == "english_only" and is_promo_valid(prof)),
        )
        await q.edit_message_text(text, reply_markup=_kb_main(ui, sess["mode"]))
        return

    # Выбор языка
    if data.startswith("S:SET:LANG:"):
        code = data.split(":", 3)[-1]
        try:
            save_user_profile(chat_id, target_lang=code)
        except Exception:
            logger.exception("Failed to save target_lang=%s", code)
        sess["target_lang"] = code

        prof = get_user_profile(chat_id) or prof
        level_now = (prof.get("level") or sess.get("level") or "B1").upper()
        append_tr = bool(prof.get("append_translation")) if level_now in ("A0", "A1") else False

        text = _main_text(
            ui=ui,
            lang_name=_name_for_lang(prof.get("target_lang") or code),
            level=prof.get("level") or sess.get("level") or "B1",
            style_name=_name_for_style(prof.get("style") or sess.get("style") or "casual", ui),
            out_mode=sess.get("mode") or "text",
            append_tr=append_tr,
            english_only_note=(prof.get("promo_type") == "english_only" and is_promo_valid(prof)),
        )
        await q.edit_message_text(text, reply_markup=_kb_settings(ui, append_tr))
        return

    # Выбор уровня
    if data.startswith("S:SET:LEVEL:"):
        level = data.split(":", 3)[-1]
        sess["level"] = level
        try:
            save_user_profile(chat_id, level=level)
        except Exception:
            logger.exception("Failed to save level=%s", level)

        prof = get_user_profile(chat_id) or prof
        append_tr = bool(prof.get("append_translation")) if level.upper() in ("A0", "A1") else False

        text = _main_text(
            ui=ui,
            lang_name=_name_for_lang(prof.get("target_lang") or sess.get("target_lang") or "en"),
            level=level,
            style_name=_name_for_style(prof.get("style") or sess.get("style") or "casual", ui),
            out_mode=sess.get("mode") or "text",
            append_tr=append_tr,
            english_only_note=(prof.get("promo_type") == "english_only" and is_promo_valid(prof)),
        )
        await q.edit_message_text(text, reply_markup=_kb_settings(ui, append_tr))
        return

    # Выбор стиля
    if data.startswith("S:SET:STYLE:"):
        style = data.split(":", 3)[-1]
        sess["style"] = style
        try:
            save_user_profile(chat_id, style=style)
        except Exception:
            logger.exception("Failed to save style=%s", style)

        prof = get_user_profile(chat_id) or prof
        level_now = (prof.get("level") or sess.get("level") or "B1").upper()
        append_tr = bool(prof.get("append_translation")) if level_now in ("A0", "A1") else False

        text = _main_text(
            ui=ui,
            lang_name=_name_for_lang(prof.get("target_lang") or sess.get("target_lang") or "en"),
            level=prof.get("level") or sess.get("level") or "B1",
            style_name=_name_for_style(style, ui),
            out_mode=sess.get("mode") or "text",
            append_tr=append_tr,
            english_only_note=(prof.get("promo_type") == "english_only" and is_promo_valid(prof)),
        )
        await q.edit_message_text(text, reply_markup=_kb_settings(ui, append_tr))
        return

    # Premium пока не трогаем (у тебя своя логика)
    logger.debug("settings: unhandled callback %r", data)
