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

CB = "S:"  # префикс для settings callback_data


# ---------------- helpers ----------------

def _name_for_lang(code: str) -> str:
    for title, c in LANGS:
        if c == code:
            return title
    return code

def _name_for_style(code: str, ui: str) -> str:
    d = STYLE_TITLES.get(code, {})
    return d.get(ui, d.get("ru", code))

def _bool_title(ui: str, v: bool) -> str:
    if ui == "ru":
        return "Вкл" if v else "Выкл"
    return "On" if v else "Off"

def _parse3(data: str) -> tuple[str, str, str]:
    """
    Парсер формата "S:KIND:VALUE" -> ("S", "KIND", "VALUE")
    Возвращает пустые строки при некорректном формате.
    """
    parts = (data or "").split(":", 2)
    if len(parts) != 3:
        return "", "", ""
    return parts[0] + ":", parts[1], parts[2]  # ("S:", "MODE", "translator")

def _get_state(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE) -> Dict[str, Any]:
    prof = get_user_profile(chat_id) or {}
    sess = user_sessions.setdefault(chat_id, {})
    ensure_tr_defaults(sess)

    # важное: всегда предпочитаем profile, иначе session, иначе user_data
    ud = ctx.user_data or {}

    target = prof.get("target_lang") or sess.get("target_lang") or ud.get("language") or "en"
    level = prof.get("level") or sess.get("level") or ud.get("level") or "B1"
    style = prof.get("style") or sess.get("style") or ud.get("style") or "casual"

    out_mode = sess.get("mode") or "text"
    if out_mode not in ("text", "voice"):
        out_mode = "text"

    task_mode = sess.get("task_mode") or "chat"
    if task_mode not in ("chat", "translator"):
        task_mode = "chat"

    append_tr = bool(prof.get("append_translation")) if str(level) in ("A0", "A1") else False
    english_only_note = (prof.get("promo_type") == "english_only" and is_promo_valid(prof))

    # синхронизация session, чтобы chat_handler не жил старыми значениями
    sess["target_lang"] = str(target)
    sess["level"] = str(level)
    sess["style"] = str(style)
    sess["mode"] = out_mode
    sess["task_mode"] = task_mode
    # append_translation в session включаем только если A0/A1
    sess["append_translation"] = bool(append_tr) if str(level) in ("A0", "A1") else False

    return {
        "prof": prof,
        "sess": sess,
        "target": str(target),
        "level": str(level),
        "style": str(style),
        "out_mode": out_mode,
        "task_mode": task_mode,
        "append_tr": bool(append_tr),
        "english_only_note": bool(english_only_note),
    }

async def _edit_or_send(update: Update, ctx: ContextTypes.DEFAULT_TYPE, text: str, kb: InlineKeyboardMarkup | None):
    q = getattr(update, "callback_query", None)
    if q and q.message:
        await q.edit_message_text(text, reply_markup=kb)
        try:
            await q.answer()
        except Exception:
            pass
        return
    await ctx.bot.send_message(update.effective_chat.id, text, reply_markup=kb)


# ---------------- texts ----------------

def _main_text(ui: str, lang_name: str, level: str, style_name: str, out_mode: str, task_mode: str, append_tr: bool, english_only_note: bool) -> str:
    fmt = "🔊 Аудио" if out_mode == "voice" else "⌨️ Текст"
    mode_title = ("🌍 Переводчик" if ui == "ru" else "🌍 Translator") if task_mode == "translator" else ("💬 Диалог" if ui == "ru" else "💬 Chat")

    if ui == "ru":
        text = (
            "⚙️ Настройки\n\n"
            f"Выбранный язык: {lang_name}\n"
            f"Установленный уровень: {level}\n"
            f"Стиль: {style_name}\n"
            f"Формат ответа Метта: {fmt}\n"
            f"Режим: {mode_title}\n"
            f"Дублирование: {_bool_title(ui, append_tr)}\n\n"
            "Что хочешь поменять?"
        )
        if english_only_note:
            text += "\n\n❗ Промокод бессрочный, действует только для английского языка"
        return text

    text = (
        "⚙️ Settings\n\n"
        f"Selected language: {lang_name}\n"
        f"Current level: {level}\n"
        f"Style: {style_name}\n"
        f"Matt’s reply format: {'🔊 Voice' if out_mode == 'voice' else '⌨️ Text'}\n"
        f"Mode: {mode_title}\n"
        f"Native duplication: {_bool_title(ui, append_tr)}\n\n"
        "What do you want to change?"
    )
    if english_only_note:
        text += "\n\n❗ Promo is permanent and limits learning to English only"
    return text


# ---------------- keyboards (Variant 1 + чекбоксы + Готово) ----------------

def _kb_main(ui: str, out_mode: str, task_mode: str) -> InlineKeyboardMarkup:
    # ✅ показываем выбранное
    txt_lbl = ("✅ ⌨️ Текст" if ui == "ru" else "✅ ⌨️ Text") if out_mode == "text" else ("⌨️ Текст" if ui == "ru" else "⌨️ Text")
    v_lbl = ("✅ 🔊 Аудио" if ui == "ru" else "✅ 🔊 Voice") if out_mode == "voice" else ("🔊 Аудио" if ui == "ru" else "🔊 Voice")

    chat_lbl = ("✅ 💬 Диалог" if ui == "ru" else "✅ 💬 Chat") if task_mode == "chat" else ("💬 Диалог" if ui == "ru" else "💬 Chat")
    tr_lbl = ("✅ 🌍 Переводчик" if ui == "ru" else "✅ 🌍 Translator") if task_mode == "translator" else ("🌍 Переводчик" if ui == "ru" else "🌍 Translator")

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(txt_lbl, callback_data=f"{CB}FMT:text"),
            InlineKeyboardButton(v_lbl, callback_data=f"{CB}FMT:voice"),
        ],
        [
            InlineKeyboardButton(chat_lbl, callback_data=f"{CB}MODE:chat"),
            InlineKeyboardButton(tr_lbl, callback_data=f"{CB}MODE:translator"),
        ],
        [
            InlineKeyboardButton("🛠 Настройки" if ui == "ru" else "🛠 Settings", callback_data=f"{CB}OPEN:SETTINGS"),
            InlineKeyboardButton("⭐ Premium", callback_data=f"{CB}OPEN:PREMIUM"),
        ],
        [
            InlineKeyboardButton("✅ Готово" if ui == "ru" else "✅ Done", callback_data=f"{CB}CLOSE:MAIN"),
        ],
    ])

def _kb_settings_sub(ui: str, append_tr: bool) -> InlineKeyboardMarkup:
    lbl_tr = ("Дублирование: Вкл" if ui == "ru" else "Native: On") if append_tr else ("Дублирование: Выкл" if ui == "ru" else "Native: Off")
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Язык" if ui == "ru" else "Language", callback_data=f"{CB}OPEN:LANG"),
            InlineKeyboardButton("Уровень" if ui == "ru" else "Level", callback_data=f"{CB}OPEN:LEVEL"),
        ],
        [
            InlineKeyboardButton("Стиль" if ui == "ru" else "Style", callback_data=f"{CB}OPEN:STYLE"),
        ],
        [
            InlineKeyboardButton(lbl_tr, callback_data=f"{CB}TOGGLE:APPEND_TR"),
        ],
        [
            InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data=f"{CB}BACK:MAIN"),
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
        rows.append([InlineKeyboardButton(t, callback_data=f"{CB}SET:LANG:{c}") for (t, c) in chunk])

    rows.append([InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data=f"{CB}OPEN:SETTINGS")])
    return InlineKeyboardMarkup(rows)

def _levels_keyboard(ui: str) -> InlineKeyboardMarkup:
    row1 = [InlineKeyboardButton(x, callback_data=f"{CB}SET:LEVEL:{x}") for x in LEVELS_ROW1]
    row2 = [InlineKeyboardButton(x, callback_data=f"{CB}SET:LEVEL:{x}") for x in LEVELS_ROW2]
    guide = InlineKeyboardButton("📘 Гайд по уровням" if ui == "ru" else "📘 Level guide", callback_data=f"{CB}LEVEL:GUIDE")
    back = InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data=f"{CB}OPEN:SETTINGS")
    return InlineKeyboardMarkup([row1, row2, [guide], [back]])

def _styles_keyboard(ui: str) -> InlineKeyboardMarkup:
    rows = []
    for code in STYLE_ORDER:
        rows.append([InlineKeyboardButton(_name_for_style(code, ui), callback_data=f"{CB}SET:STYLE:{code}")])
    rows.append([InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data=f"{CB}OPEN:SETTINGS")])
    return InlineKeyboardMarkup(rows)

def _kb_level_guide(ui: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data=f"{CB}LEVEL:GUIDE:CLOSE")]
    ])

def _kb_premium(ui: str) -> InlineKeyboardMarkup:
    buy = InlineKeyboardButton("Купить" if ui == "ru" else "Buy", callback_data=f"{CB}PREM:BUY")
    donate = InlineKeyboardButton("Донат" if ui == "ru" else "Donate", callback_data=f"{CB}PREM:DONATE")
    how = InlineKeyboardButton("Как оплатить" if ui == "ru" else "How to pay", callback_data=f"{CB}PREM:HOW")
    back = InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data=f"{CB}BACK:MAIN")
    return InlineKeyboardMarkup([[buy, donate], [how], [back]])


# ---------------- commands ----------------

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ui = get_ui_lang(update, context)
    chat_id = update.effective_chat.id
    st = _get_state(chat_id, context)

    text = _main_text(
        ui=ui,
        lang_name=_name_for_lang(st["target"]),
        level=st["level"],
        style_name=_name_for_style(st["style"], ui),
        out_mode=st["out_mode"],
        task_mode=st["task_mode"],
        append_tr=st["append_tr"],
        english_only_note=st["english_only_note"],
    )
    await _edit_or_send(update, context, text, _kb_main(ui, st["out_mode"], st["task_mode"]))

# Алиасы: /voice /text /translation /chat
async def cmd_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    sess["mode"] = "voice"
    ui = get_ui_lang(update, context)
    await update.effective_message.reply_text("🔊 Теперь отвечаю аудио." if ui == "ru" else "🔊 Now I reply with voice.")

async def cmd_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    sess["mode"] = "text"
    ui = get_ui_lang(update, context)
    await update.effective_message.reply_text("⌨️ Теперь отвечаю текстом." if ui == "ru" else "⌨️ Now I reply with text.")

async def cmd_translation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    sess["task_mode"] = "translator"
    ensure_tr_defaults(sess)
    await enter_translator(update, context, sess)

async def cmd_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    if sess.get("task_mode") == "translator":
        await exit_translator(update, context, sess)
    sess["task_mode"] = "chat"
    ui = get_ui_lang(update, context)
    await update.effective_message.reply_text("💬 Диалоговый режим включён." if ui == "ru" else "💬 Chat mode is ON.")


# ---------------- callback router ----------------

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.data:
        return

    data = q.data
    if not data.startswith(CB):
        return

    ui = get_ui_lang(update, context)
    chat_id = q.message.chat.id
    st = _get_state(chat_id, context)
    sess = st["sess"]
    prof = st["prof"]

    # Закрыть меню (убрать клавиатуру)
    if data == f"{CB}CLOSE:MAIN":
        await q.edit_message_text("✅ Готово." if ui == "ru" else "✅ Done.", reply_markup=None)
        await q.answer("✅")
        return

    # Навигация
    if data == f"{CB}BACK:MAIN":
        await cmd_settings(update, context)
        return

    if data == f"{CB}OPEN:SETTINGS":
        await q.edit_message_text("🛠 Настройки" if ui == "ru" else "🛠 Settings", reply_markup=_kb_settings_sub(ui, st["append_tr"]))
        await q.answer()
        return

    if data == f"{CB}OPEN:PREMIUM":
        await q.edit_message_text("⭐ Премиум" if ui == "ru" else "⭐ Premium", reply_markup=_kb_premium(ui))
        await q.answer()
        return

    # Premium actions — не ломаем существующие потоки оплаты
    if data == f"{CB}PREM:BUY":
        await q.answer("✅")
        await context.bot.send_message(chat_id, "Открой /buy" if ui == "ru" else "Open /buy")
        return
    if data == f"{CB}PREM:DONATE":
        await q.answer("✅")
        await context.bot.send_message(chat_id, "Открой /donate" if ui == "ru" else "Open /donate")
        return
    if data == f"{CB}PREM:HOW":
        await q.answer("✅")
        await context.bot.send_message(chat_id, "Смотри /buy → «Как оплатить»" if ui == "ru" else "Open /buy → “How to pay”")
        return

    # Окна выбора
    if data == f"{CB}OPEN:LANG":
        await q.edit_message_text("Выбери язык:" if ui == "ru" else "Choose a language:", reply_markup=_langs_keyboard(chat_id, ui))
        await q.answer()
        return

    if data == f"{CB}OPEN:LEVEL":
        await q.edit_message_text("Выбери уровень:" if ui == "ru" else "Choose your level:", reply_markup=_levels_keyboard(ui))
        await q.answer()
        return

    if data == f"{CB}OPEN:STYLE":
        await q.edit_message_text("Выбери стиль:" if ui == "ru" else "Choose a style:", reply_markup=_styles_keyboard(ui))
        await q.answer()
        return

    # Гайд уровней
    if data == f"{CB}LEVEL:GUIDE":
        guide_text = None
        try:
            from handlers.chat.levels_text import get_level_guide  # type: ignore
            guide_text = get_level_guide(ui)
        except Exception:
            guide_text = None

        text = guide_text or ("Гайд временно недоступен." if ui == "ru" else "Guide is temporarily unavailable.")
        await q.edit_message_text(text=text, reply_markup=_kb_level_guide(ui), parse_mode="Markdown")
        await q.answer()
        return

    if data == f"{CB}LEVEL:GUIDE:CLOSE":
        await q.edit_message_text("Выбери уровень:" if ui == "ru" else "Choose your level:", reply_markup=_levels_keyboard(ui))
        await q.answer()
        return

    # Переключение формата/режима (FIX парсинга!)
    prefix, kind, val = _parse3(data)

    if prefix == CB and kind == "FMT" and val in ("text", "voice"):
        sess["mode"] = val
        await q.answer("✅")
        await cmd_settings(update, context)
        return

    if prefix == CB and kind == "MODE" and val in ("chat", "translator"):
        if val == "translator":
            sess["task_mode"] = "translator"
            ensure_tr_defaults(sess)
            await q.answer("✅")
            await enter_translator(update, context, sess)  # инструкция переводчика отдельным сообщением
        else:
            if sess.get("task_mode") == "translator":
                await exit_translator(update, context, sess)
            sess["task_mode"] = "chat"
            await q.answer("✅")
        await cmd_settings(update, context)
        return

    # Тумблер дубля (A0/A1)
    if data == f"{CB}TOGGLE:APPEND_TR":
        level = st["level"]
        if level not in ("A0", "A1"):
            await q.answer("Недоступно для вашего уровня" if ui == "ru" else "Unavailable for your level", show_alert=True)
            return

        new_val = not bool(prof.get("append_translation"))
        try:
            save_user_profile(chat_id, append_translation=new_val, append_translation_lang=(prof.get("interface_lang") or ("ru" if ui == "ru" else "en")))
        except Exception:
            logger.debug("append_translation save failed", exc_info=True)

        # ВАЖНО: включаем и в session тоже
        sess["append_translation"] = bool(new_val)

        await q.answer("✅")
        # остаёмся в подменю настроек
        st2 = _get_state(chat_id, context)
        await q.edit_message_text("🛠 Настройки" if ui == "ru" else "🛠 Settings", reply_markup=_kb_settings_sub(ui, st2["append_tr"]))
        return

    # Применение выбора
    if data.startswith(f"{CB}SET:LANG:"):
        code = data.split(":", 3)[-1]
        sess["target_lang"] = code
        (context.user_data or {})["language"] = code
        try:
            save_user_profile(chat_id, target_lang=code)
        except Exception:
            logger.debug("save target_lang failed", exc_info=True)
        await q.answer("✅")
        await cmd_settings(update, context)
        return

    if data.startswith(f"{CB}SET:LEVEL:"):
        lev = data.split(":", 3)[-1]
        sess["level"] = lev
        (context.user_data or {})["level"] = lev
        try:
            save_user_profile(chat_id, level=lev)
        except Exception:
            logger.debug("save level failed", exc_info=True)
        await q.answer("✅")
        await cmd_settings(update, context)
        return

    if data.startswith(f"{CB}SET:STYLE:"):
        style = data.split(":", 3)[-1]
        sess["style"] = style
        (context.user_data or {})["style"] = style
        try:
            save_user_profile(chat_id, style=style)
        except Exception:
            logger.debug("save style failed", exc_info=True)
        await q.answer("✅")
        await cmd_settings(update, context)
        return

    await q.answer()
