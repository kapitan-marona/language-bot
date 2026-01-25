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

from handlers.translator_mode import enter_translator, exit_translator, ensure_tr_defaults  # type: ignore

logger = logging.getLogger(__name__)

# -------------------- UI popup feedback (compact) --------------------

POPUP = {
    "ru": {
        "saved": "Сохранено",
        "voice": "✓ Аудио",
        "text": "✓ Текст",
        "chat": "✓ Диалог",
        "translator": "✓ Переводчик",
        "lang": "✓ Язык изменён",
        "level": "✓ Уровень",
        "style": "✓ Стиль",
        "append_on": "✓ Дублирование: Вкл",
        "append_off": "✓ Дублирование: Выкл",
        "unavailable": "Недоступно для вашего уровня",
    },
    "en": {
        "saved": "Saved",
        "voice": "✓ Voice",
        "text": "✓ Text",
        "chat": "✓ Chat",
        "translator": "✓ Translator",
        "lang": "✓ Language updated",
        "level": "✓ Level",
        "style": "✓ Style",
        "append_on": "✓ Native: On",
        "append_off": "✓ Native: Off",
        "unavailable": "Unavailable for your level",
    },
}

def popup(ui: str, key: str) -> str:
    return POPUP.get(ui, POPUP["en"]).get(key, POPUP["en"]["saved"])

# -------------------- constants --------------------

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
    "casual":   {"ru": "😎 Разговорный", "en": "😎 Casual"},
    "business": {"ru": "🤓 Деловой",     "en": "🤓 Business"},
}
STYLE_ORDER = ["casual", "business"]

# -------------------- small helpers --------------------

def _name_for_lang(code: str) -> str:
    for title, c in LANGS:
        if c == code:
            return title
    return code or "en"

def _name_for_style(code: str, ui: str) -> str:
    d = STYLE_TITLES.get(code or "", {})
    return d.get(ui, d.get("en", code or "casual"))

def _get_state(chat_id: int) -> Dict[str, Any]:
    """
    Единый источник текущих настроек: session + profile.
    """
    sess = user_sessions.setdefault(chat_id, {})
    prof = get_user_profile(chat_id) or {}

    out_mode = (sess.get("mode") or "text")
    if out_mode not in ("text", "voice"):
        out_mode = "text"

    task_mode = (sess.get("task_mode") or "chat")
    if task_mode not in ("chat", "translator"):
        task_mode = "chat"

    tgt = (prof.get("target_lang") or sess.get("target_lang") or "en")
    lvl = (prof.get("level") or sess.get("level") or "B1")
    stl = (prof.get("style") or sess.get("style") or "casual")

    append_tr = False
    try:
        if str(lvl).upper() in ("A0", "A1"):
            append_tr = bool(prof.get("append_translation"))
    except Exception:
        append_tr = False

    english_only_note = bool(prof.get("promo_type") == "english_only" and is_promo_valid(prof))

    return {
        "sess": sess,
        "prof": prof,
        "target_lang": str(tgt),
        "level": str(lvl).upper(),
        "style": str(stl),
        "out_mode": out_mode,
        "task_mode": task_mode,
        "append_tr": append_tr,
        "english_only_note": english_only_note,
    }

async def _edit_or_send(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, kb: InlineKeyboardMarkup):
    q = getattr(update, "callback_query", None)
    if q and q.message:
        await q.edit_message_text(text, reply_markup=kb)
        return
    await context.bot.send_message(update.effective_chat.id, text, reply_markup=kb)

def _main_text(
    ui: str,
    *,
    lang_name: str,
    level: str,
    style_name: str,
    out_mode: str,
    task_mode: str,
    append_tr: bool,
    english_only_note: bool,
) -> str:
    fmt_title = ("🔊 Аудио" if ui == "ru" else "🔊 Voice") if out_mode == "voice" else ("⌨️ Текст" if ui == "ru" else "⌨️ Text")
    mode_title = ("🌍 Переводчик" if ui == "ru" else "🌍 Translator") if task_mode == "translator" else ("💬 Диалог" if ui == "ru" else "💬 Chat")
    dup_title = ("Вкл" if ui == "ru" else "On") if append_tr else ("Выкл" if ui == "ru" else "Off")

    text_ru = (
        "⚙️ Настройки\n\n"
        f"Выбранный язык: {lang_name}\n"
        f"Установленный уровень: {level}\n"
        f"Стиль: {style_name}\n"
        f"Формат ответа Метта: {fmt_title}\n"
        f"Режим: {mode_title}\n"
        f"Дублирование: {dup_title}"
    )
    text_en = (
        "⚙️ Settings\n\n"
        f"Selected language: {lang_name}\n"
        f"Level: {level}\n"
        f"Style: {style_name}\n"
        f"Matt’s output: {fmt_title}\n"
        f"Mode: {mode_title}\n"
        f"Native duplication: {dup_title}"
    )

    text = text_ru if ui == "ru" else text_en
    if english_only_note:
        text += ("\n\n❗ Промокод бессрочный, действует только для английского языка"
                 if ui == "ru" else
                 "\n\n❗ Promo is permanent and limits learning to English only")
    return text

# -------------------- keyboards --------------------

def _kb_main(ui: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⌨️ Текст" if ui == "ru" else "⌨️ Text", callback_data="S:FORMAT:text"),
            InlineKeyboardButton("🔊 Аудио" if ui == "ru" else "🔊 Voice", callback_data="S:FORMAT:voice"),
        ],
        [
            InlineKeyboardButton("💬 Диалог" if ui == "ru" else "💬 Chat", callback_data="S:MODE:chat"),
            InlineKeyboardButton("🌍 Переводчик" if ui == "ru" else "🌍 Translator", callback_data="S:MODE:translator"),
        ],
        [
            InlineKeyboardButton("🛠 Настройки" if ui == "ru" else "🛠 Settings", callback_data="S:OPEN:SETTINGS"),
            InlineKeyboardButton("⭐ Premium", callback_data="S:OPEN:PREMIUM"),
        ],
    ])

def _kb_settings(ui: str, append_tr: bool) -> InlineKeyboardMarkup:
    btn_dup = ("Дублирование: Вкл" if ui == "ru" else "Native: On") if append_tr else ("Дублирование: Выкл" if ui == "ru" else "Native: Off")
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Язык" if ui == "ru" else "Language", callback_data="S:OPEN:LANG"),
            InlineKeyboardButton("Уровень" if ui == "ru" else "Level", callback_data="S:OPEN:LEVEL"),
        ],
        [
            InlineKeyboardButton("Стиль" if ui == "ru" else "Style", callback_data="S:OPEN:STYLE"),
            InlineKeyboardButton(btn_dup, callback_data="S:TOGGLE:APPEND_TR"),
        ],
        [
            InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:BACK:MAIN"),
        ]
    ])

def _kb_langs(chat_id: int, ui: str) -> InlineKeyboardMarkup:
    prof = get_user_profile(chat_id) or {}
    lang_map = {code: title for title, code in LANGS}
    lang_map = restrict_target_languages_if_needed(prof, lang_map)

    items = [(title, code) for code, title in lang_map.items()]
    rows = []
    for i in range(0, len(items), 2):
        chunk = items[i:i+2]
        rows.append([InlineKeyboardButton(t, callback_data=f"S:LANG:{c}") for (t, c) in chunk])

    rows.append([InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:OPEN:SETTINGS")])
    return InlineKeyboardMarkup(rows)

def _kb_levels(ui: str) -> InlineKeyboardMarkup:
    row1 = [InlineKeyboardButton(x, callback_data=f"S:LEVEL:{x}") for x in LEVELS_ROW1]
    row2 = [InlineKeyboardButton(x, callback_data=f"S:LEVEL:{x}") for x in LEVELS_ROW2]
    guide = InlineKeyboardButton("ℹ️ Гайд по уровням" if ui == "ru" else "ℹ️ Level guide", callback_data="S:LEVEL:GUIDE")
    back = InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:OPEN:SETTINGS")
    return InlineKeyboardMarkup([row1, row2, [guide], [back]])

def _kb_level_guide(ui: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:OPEN:LEVEL")]
    ])

def _kb_styles(ui: str) -> InlineKeyboardMarkup:
    rows = []
    for code in STYLE_ORDER:
        rows.append([InlineKeyboardButton(_name_for_style(code, ui), callback_data=f"S:STYLE:{code}")])
    rows.append([InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:OPEN:SETTINGS")])
    return InlineKeyboardMarkup(rows)

def _kb_premium(ui: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛒 Купить" if ui == "ru" else "🛒 Buy", callback_data="S:PREM:BUY"),
            InlineKeyboardButton("💜 Донат" if ui == "ru" else "💜 Donate", callback_data="S:PREM:DONATE"),
        ],
        [InlineKeyboardButton("❓ Как оплатить" if ui == "ru" else "❓ How to pay", callback_data="S:PREM:HOW")],
        [InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:BACK:MAIN")],
    ])

# -------------------- commands --------------------

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ui = get_ui_lang(update, context)
    chat_id = update.effective_chat.id
    st = _get_state(chat_id)

    text = _main_text(
        ui,
        lang_name=_name_for_lang(st["target_lang"]),
        level=st["level"],
        style_name=_name_for_style(st["style"], ui),
        out_mode=st["out_mode"],
        task_mode=st["task_mode"],
        append_tr=st["append_tr"],
        english_only_note=st["english_only_note"],
    )
    await _edit_or_send(update, context, text, _kb_main(ui))

async def cmd_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Alias: /voice — just switch mode to voice."""
    ui = get_ui_lang(update, context)
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    sess["mode"] = "voice"
    await update.effective_message.reply_text("🔊 Ок, отвечаю аудио." if ui == "ru" else "🔊 Ok, I’ll reply with voice.")

async def cmd_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Alias: /text — just switch mode to text."""
    ui = get_ui_lang(update, context)
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    sess["mode"] = "text"
    await update.effective_message.reply_text("⌨️ Ок, отвечаю текстом." if ui == "ru" else "⌨️ Ok, I’ll reply with text.")

async def cmd_translation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Alias: /translation — enable translator mode."""
    ui = get_ui_lang(update, context)
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    ensure_tr_defaults(sess)
    sess["task_mode"] = "translator"
    await update.effective_message.reply_text("🌍 Ок, включаю переводчик." if ui == "ru" else "🌍 Ok, enabling translator.")
    await enter_translator(update, context, sess)

async def cmd_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Alias: /chat — back to chat mode."""
    ui = get_ui_lang(update, context)
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    sess["task_mode"] = "chat"
    try:
        await exit_translator(update, context, sess)
    except Exception:
        pass
    await update.effective_message.reply_text("💬 Ок, возвращаю диалог." if ui == "ru" else "💬 Ok, back to chat mode.")

# -------------------- callbacks --------------------

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.data:
        return

    ui = get_ui_lang(update, context)
    chat_id = q.message.chat.id
    sess = user_sessions.setdefault(chat_id, {})
    ensure_tr_defaults(sess)

    data = q.data

    if data == "S:BACK:MAIN":
        await q.answer()
        await cmd_settings(update, context)
        return

    if data == "S:OPEN:SETTINGS":
        st = _get_state(chat_id)
        text = _main_text(
            ui,
            lang_name=_name_for_lang(st["target_lang"]),
            level=st["level"],
            style_name=_name_for_style(st["style"], ui),
            out_mode=st["out_mode"],
            task_mode=st["task_mode"],
            append_tr=st["append_tr"],
            english_only_note=st["english_only_note"],
        )
        await q.answer()
        await _edit_or_send(update, context, text, _kb_settings(ui, st["append_tr"]))
        return

    if data == "S:OPEN:LANG":
        await q.answer()
        await q.edit_message_text(
            "Выбери язык:" if ui == "ru" else "Choose a language:",
            reply_markup=_kb_langs(chat_id, ui),
        )
        return

    if data == "S:OPEN:LEVEL":
        await q.answer()
        await q.edit_message_text(
            "Выбери уровень:" if ui == "ru" else "Choose your level:",
            reply_markup=_kb_levels(ui),
        )
        return

    if data == "S:LEVEL:GUIDE":
        guide_text = None
        try:
            from components.onboarding import get_level_guide  # type: ignore
            guide_text = get_level_guide(ui)
        except Exception:
            guide_text = None

        txt = guide_text or ("Гайд временно недоступен." if ui == "ru" else "Guide is temporarily unavailable.")
        await q.answer()
        await q.edit_message_text(txt, reply_markup=_kb_level_guide(ui), parse_mode="Markdown")
        return

    if data == "S:OPEN:STYLE":
        await q.answer()
        await q.edit_message_text(
            "Выбери стиль общения:" if ui == "ru" else "Choose a chat style:",
            reply_markup=_kb_styles(ui),
        )
        return

    if data == "S:OPEN:PREMIUM":
        await q.answer()
        await q.edit_message_text(
            "⭐ Премиум" if ui == "ru" else "⭐ Premium",
            reply_markup=_kb_premium(ui),
        )
        return

    # format
    if data.startswith("S:FORMAT:"):
        _, _, val = data.split(":", 2)
        sess["mode"] = "voice" if val == "voice" else "text"

        st = _get_state(chat_id)
        text = _main_text(
            ui,
            lang_name=_name_for_lang(st["target_lang"]),
            level=st["level"],
            style_name=_name_for_style(st["style"], ui),
            out_mode=st["out_mode"],
            task_mode=st["task_mode"],
            append_tr=st["append_tr"],
            english_only_note=st["english_only_note"],
        )

        await q.answer(popup(ui, "voice" if sess["mode"] == "voice" else "text"))
        await q.edit_message_text(text, reply_markup=_kb_main(ui))
        return

    # mode
    if data.startswith("S:MODE:"):
        _, _, val = data.split(":", 2)
        if val == "translator":
            sess["task_mode"] = "translator"
            await q.answer(popup(ui, "translator"))
            await enter_translator(update, context, sess)
        else:
            sess["task_mode"] = "chat"
            await q.answer(popup(ui, "chat"))
            try:
                await exit_translator(update, context, sess)
            except Exception:
                pass

        st = _get_state(chat_id)
        text = _main_text(
            ui,
            lang_name=_name_for_lang(st["target_lang"]),
            level=st["level"],
            style_name=_name_for_style(st["style"], ui),
            out_mode=st["out_mode"],
            task_mode=st["task_mode"],
            append_tr=st["append_tr"],
            english_only_note=st["english_only_note"],
        )
        try:
            await q.edit_message_text(text, reply_markup=_kb_main(ui))
        except Exception:
            pass
        return

    # duplication (A0-A1 only)
    if data == "S:TOGGLE:APPEND_TR":
        prof = get_user_profile(chat_id) or {}
        lvl = (prof.get("level") or sess.get("level") or "B1").upper()

        if lvl in ("A0", "A1"):
            new_val = not bool(prof.get("append_translation"))
            try:
                save_user_profile(
                    chat_id,
                    append_translation=new_val,
                    append_translation_lang=(prof.get("interface_lang") or "en"),
                )
            except Exception:
                logger.exception("Failed to save append_translation")

            await q.answer(popup(ui, "append_on" if new_val else "append_off"))

            st = _get_state(chat_id)
            text = _main_text(
                ui,
                lang_name=_name_for_lang(st["target_lang"]),
                level=st["level"],
                style_name=_name_for_style(st["style"], ui),
                out_mode=st["out_mode"],
                task_mode=st["task_mode"],
                append_tr=st["append_tr"],
                english_only_note=st["english_only_note"],
            )
            await q.edit_message_text(text, reply_markup=_kb_settings(ui, st["append_tr"]))
            return

        await q.answer(popup(ui, "unavailable"), show_alert=True)
        return

    # apply language/level/style
    if data.startswith("S:LANG:"):
        code = data.split(":", 2)[-1]
        sess["target_lang"] = code
        try:
            save_user_profile(chat_id, target_lang=code)
        except Exception:
            logger.debug("save target_lang failed", exc_info=True)

        await q.answer(popup(ui, "lang"))

        st = _get_state(chat_id)
        text = _main_text(
            ui,
            lang_name=_name_for_lang(st["target_lang"]),
            level=st["level"],
            style_name=_name_for_style(st["style"], ui),
            out_mode=st["out_mode"],
            task_mode=st["task_mode"],
            append_tr=st["append_tr"],
            english_only_note=st["english_only_note"],
        )
        await q.edit_message_text(text, reply_markup=_kb_settings(ui, st["append_tr"]))
        return

    if data.startswith("S:LEVEL:") and data.count(":") == 2:
        level = data.split(":", 2)[-1].upper()
        sess["level"] = level
        try:
            save_user_profile(chat_id, level=level)
        except Exception:
            logger.debug("save level failed", exc_info=True)

        await q.answer(popup(ui, "level"))

        st = _get_state(chat_id)
        text = _main_text(
            ui,
            lang_name=_name_for_lang(st["target_lang"]),
            level=st["level"],
            style_name=_name_for_style(st["style"], ui),
            out_mode=st["out_mode"],
            task_mode=st["task_mode"],
            append_tr=st["append_tr"],
            english_only_note=st["english_only_note"],
        )
        await q.edit_message_text(text, reply_markup=_kb_settings(ui, st["append_tr"]))
        return

    if data.startswith("S:STYLE:"):
        style = data.split(":", 2)[-1]
        sess["style"] = style
        try:
            save_user_profile(chat_id, style=style)
        except Exception:
            logger.debug("save style failed", exc_info=True)

        await q.answer(popup(ui, "style"))

        st = _get_state(chat_id)
        text = _main_text(
            ui,
            lang_name=_name_for_lang(st["target_lang"]),
            level=st["level"],
            style_name=_name_for_style(st["style"], ui),
            out_mode=st["out_mode"],
            task_mode=st["task_mode"],
            append_tr=st["append_tr"],
            english_only_note=st["english_only_note"],
        )
        await q.edit_message_text(text, reply_markup=_kb_settings(ui, st["append_tr"]))
        return

    # premium actions (keep existing flows)
    if data == "S:PREM:BUY":
        await q.answer(popup(ui, "saved"))
        await context.bot.send_message(chat_id, "/buy")
        return

    if data == "S:PREM:DONATE":
        await q.answer(popup(ui, "saved"))
        await context.bot.send_message(chat_id, "/donate")
        return

    if data == "S:PREM:HOW":
        await q.answer(popup(ui, "saved"))
        try:
            from handlers.callbacks import how_to_pay_game
            await how_to_pay_game.how_to_pay_entry(update, context)
        except Exception:
            await context.bot.send_message(chat_id, "Напиши /buy и нажми «Как оплатить»." if ui == "ru" else "Type /buy and tap “How to pay”.")
        return

    await q.answer()
    logger.warning("Unhandled settings callback: %r", data)
