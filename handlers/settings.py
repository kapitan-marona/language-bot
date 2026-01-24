# handlers/settings.py
from __future__ import annotations

import logging
from typing import Dict, Any, List, Tuple, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from components.profile_db import get_user_profile, save_user_profile
from components.promo import restrict_target_languages_if_needed, is_promo_valid
from components.i18n import get_ui_lang
from state.session import user_sessions

# Переводчик: вход/выход и дефолты
from handlers.translator_mode import enter_translator, exit_translator, ensure_tr_defaults  # type: ignore

logger = logging.getLogger(__name__)

# --- данные для выбора языка (как раньше) ---
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

# --- callbacks prefix ---
# ВАЖНО: всё меню settings — только через "S:" чтобы не пересекаться с онбордингом/прочими.
CB = "S:"

# --- helpers ---

def _name_for_lang(code: str) -> str:
    for title, c in LANGS:
        if c == code:
            return title
    return code

def _name_for_style(code: str, ui: str) -> str:
    d = STYLE_TITLES.get(code, {})
    return d.get(ui, d.get("ru", code))

def _bool_title(ui: str, v: bool, on_ru="Вкл", off_ru="Выкл", on_en="On", off_en="Off") -> str:
    if ui == "ru":
        return on_ru if v else off_ru
    return on_en if v else off_en

def _get_state(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE) -> Dict[str, Any]:
    """
    Единая точка правды для /settings.
    Берём значения из профиля (если есть), иначе — из session/user_data, иначе дефолты.
    """
    prof = get_user_profile(chat_id) or {}
    sess = user_sessions.setdefault(chat_id, {})
    ensure_tr_defaults(sess)

    # target language
    target = prof.get("target_lang") or sess.get("target_lang") or (ctx.user_data or {}).get("language") or "en"
    # level
    level = prof.get("level") or sess.get("level") or (ctx.user_data or {}).get("level") or "B1"
    # style
    style = prof.get("style") or sess.get("style") or (ctx.user_data or {}).get("style") or "casual"

    # reply format: voice/text -> sess["mode"] (как уже у тебя используется)
    out_mode = sess.get("mode") or "text"
    if out_mode not in ("text", "voice"):
        out_mode = "text"

    # task_mode: chat/translator
    task_mode = sess.get("task_mode") or "chat"
    if task_mode not in ("chat", "translator"):
        task_mode = "chat"

    # append_translation (только A0/A1 по твоей логике)
    append_tr = bool(prof.get("append_translation")) if str(level) in ("A0", "A1") else False

    english_only_note = (prof.get("promo_type") == "english_only" and is_promo_valid(prof))

    return {
        "prof": prof,
        "sess": sess,
        "target": str(target),
        "level": str(level),
        "style": str(style),
        "out_mode": out_mode,
        "task_mode": task_mode,
        "append_tr": append_tr,
        "english_only_note": bool(english_only_note),
    }

async def _edit_or_send(update: Update, ctx: ContextTypes.DEFAULT_TYPE, text: str, kb: InlineKeyboardMarkup) -> None:
    q = getattr(update, "callback_query", None)
    if q and q.message:
        await q.edit_message_text(text, reply_markup=kb)
        try:
            await q.answer()
        except Exception:
            pass
        return
    await ctx.bot.send_message(update.effective_chat.id, text, reply_markup=kb)

# --- UI texts ---

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
            f"Дублирование: {_bool_title(ui, append_tr, on_ru='Вкл', off_ru='Выкл')}\n\n"
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
        f"Native duplication: {_bool_title(ui, append_tr, on_en='On', off_en='Off')}\n\n"
        "What do you want to change?"
    )
    if english_only_note:
        text += "\n\n❗ Promo is permanent and limits learning to English only"
    return text

# --- keyboards (Variant 1 clean) ---

def _kb_main(ui: str) -> InlineKeyboardMarkup:
    # Вариант 1 (самый чистый)
    # ⌨️ Текст | 🔊 Аудио
    # 💬 Диалог | 🌍 Переводчик
    # 🛠 Настройки | ⭐ Premium
    btn_text = InlineKeyboardButton("⌨️ Текст" if ui == "ru" else "⌨️ Text", callback_data=f"{CB}FMT:text")
    btn_voice = InlineKeyboardButton("🔊 Аудио" if ui == "ru" else "🔊 Voice", callback_data=f"{CB}FMT:voice")

    btn_chat = InlineKeyboardButton("💬 Диалог" if ui == "ru" else "💬 Chat", callback_data=f"{CB}MODE:chat")
    btn_tr = InlineKeyboardButton("🌍 Переводчик" if ui == "ru" else "🌍 Translator", callback_data=f"{CB}MODE:translator")

    btn_settings = InlineKeyboardButton("🛠 Настройки" if ui == "ru" else "🛠 Settings", callback_data=f"{CB}OPEN:SETTINGS")
    btn_premium = InlineKeyboardButton("⭐ Premium", callback_data=f"{CB}OPEN:PREMIUM")

    return InlineKeyboardMarkup([
        [btn_text, btn_voice],
        [btn_chat, btn_tr],
        [btn_settings, btn_premium],
    ])

def _kb_settings_sub(ui: str, append_tr: bool) -> InlineKeyboardMarkup:
    btn_lang = InlineKeyboardButton("Язык" if ui == "ru" else "Language", callback_data=f"{CB}OPEN:LANG")
    btn_level = InlineKeyboardButton("Уровень" if ui == "ru" else "Level", callback_data=f"{CB}OPEN:LEVEL")
    btn_style = InlineKeyboardButton("Стиль" if ui == "ru" else "Style", callback_data=f"{CB}OPEN:STYLE")

    lbl_tr = ("Дублирование: Вкл" if ui == "ru" else "Native: On") if append_tr else ("Дублирование: Выкл" if ui == "ru" else "Native: Off")
    btn_tr = InlineKeyboardButton(lbl_tr, callback_data=f"{CB}TOGGLE:APPEND_TR")

    btn_back = InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data=f"{CB}BACK:MAIN")

    return InlineKeyboardMarkup([
        [btn_lang, btn_level],
        [btn_style],
        [btn_tr],
        [btn_back],
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

    rows.append([InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data=f"{CB}BACK:SETTINGS")])
    return InlineKeyboardMarkup(rows)

def _levels_keyboard(ui: str) -> InlineKeyboardMarkup:
    row1 = [InlineKeyboardButton(x, callback_data=f"{CB}SET:LEVEL:{x}") for x in LEVELS_ROW1]
    row2 = [InlineKeyboardButton(x, callback_data=f"{CB}SET:LEVEL:{x}") for x in LEVELS_ROW2]

    # Гайд по уровням — как на онбординге, но callback свой (чтобы не ломать онбординг)
    guide = InlineKeyboardButton("📘 Гайд по уровням" if ui == "ru" else "📘 Level guide", callback_data=f"{CB}LEVEL:GUIDE")
    back = InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data=f"{CB}BACK:SETTINGS")

    return InlineKeyboardMarkup([row1, row2, [guide], [back]])

def _styles_keyboard(ui: str) -> InlineKeyboardMarkup:
    rows = []
    for code in STYLE_ORDER:
        title = _name_for_style(code, ui)
        rows.append([InlineKeyboardButton(title, callback_data=f"{CB}SET:STYLE:{code}")])
    rows.append([InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data=f"{CB}BACK:SETTINGS")])
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
    return InlineKeyboardMarkup([
        [buy, donate],
        [how],
        [back],
    ])

# --- public entry ---

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
    await _edit_or_send(update, context, text, _kb_main(ui))

# --- alias commands (как вы хотели) ---

async def cmd_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    sess["mode"] = "voice"
    await cmd_settings(update, context)

async def cmd_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    sess["mode"] = "text"
    await cmd_settings(update, context)

async def cmd_translation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    sess["task_mode"] = "translator"
    ensure_tr_defaults(sess)
    # покажем инструкцию переводчика (отдельным сообщением)
    await enter_translator(update, context, sess)
    # и обновим /settings (чтобы режим был виден)
    await cmd_settings(update, context)

async def cmd_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    sess = user_sessions.setdefault(chat_id, {})
    if sess.get("task_mode") == "translator":
        await exit_translator(update, context, sess)
    sess["task_mode"] = "chat"
    await cmd_settings(update, context)

# --- callback router for settings ---

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

    # ---------- navigation ----------
    if data == f"{CB}BACK:MAIN":
        await cmd_settings(update, context)
        return

    if data == f"{CB}BACK:SETTINGS":
        # открыть подменю настроек
        txt = "🛠 Настройки" if ui == "ru" else "🛠 Settings"
        await _edit_or_send(update, context, txt, _kb_settings_sub(ui, st["append_tr"]))
        return

    if data == f"{CB}OPEN:SETTINGS":
        txt = "🛠 Настройки" if ui == "ru" else "🛠 Settings"
        await _edit_or_send(update, context, txt, _kb_settings_sub(ui, st["append_tr"]))
        return

    if data == f"{CB}OPEN:PREMIUM":
        txt = "⭐ Premium" if ui != "ru" else "⭐ Премиум"
        await _edit_or_send(update, context, txt, _kb_premium(ui))
        return

    # ---------- premium actions (без изменения бизнес-логики) ----------
    # Здесь мы не реализуем оплату внутри settings: просто мягко направляем на команды,
    # чтобы не ломать существующие pay flows.
    if data == f"{CB}PREM:BUY":
        await q.answer()
        await context.bot.send_message(chat_id, "Ок! Открой /buy" if ui == "ru" else "Ok! Use /buy")
        return

    if data == f"{CB}PREM:DONATE":
        await q.answer()
        await context.bot.send_message(chat_id, "Ок! Открой /donate" if ui == "ru" else "Ok! Use /donate")
        return

    if data == f"{CB}PREM:HOW":
        await q.answer()
        # у тебя уже есть how_to_pay_game через меню, поэтому просто подскажем /buy или кнопку в оплате
        await context.bot.send_message(chat_id, "Смотри /buy → «Как оплатить»" if ui == "ru" else "Open /buy → “How to pay”")
        return

    # ---------- open screens ----------
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

    # ---------- level guide ----------
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

    # ---------- toggles main (Variant 1) ----------
    if data.startswith(f"{CB}FMT:"):
        _, val = data.split(":", 1)
        if val in ("text", "voice"):
            sess["mode"] = val
        await cmd_settings(update, context)
        return

    if data.startswith(f"{CB}MODE:"):
        _, val = data.split(":", 1)
        if val == "translator":
            sess["task_mode"] = "translator"
            ensure_tr_defaults(sess)
            # ВАЖНО: отправим инструкцию переводчика отдельным сообщением, как у тебя сейчас сделано
            await enter_translator(update, context, sess)
        else:
            # chat
            if sess.get("task_mode") == "translator":
                await exit_translator(update, context, sess)
            sess["task_mode"] = "chat"

        await cmd_settings(update, context)
        return

    # ---------- settings sub toggles ----------
    if data == f"{CB}TOGGLE:APPEND_TR":
        level = st["level"]
        if level not in ("A0", "A1"):
            await q.answer("Недоступно для вашего уровня" if ui == "ru" else "Unavailable for your level", show_alert=True)
            return

        new_val = not bool(prof.get("append_translation"))
        try:
            save_user_profile(chat_id, append_translation=new_val, append_translation_lang=(prof.get("interface_lang") or "en"))
        except Exception:
            logger.debug("append_translation save failed", exc_info=True)

        # обновим экран настроек (подменю)
        st2 = _get_state(chat_id, context)
        txt = "🛠 Настройки" if ui == "ru" else "🛠 Settings"
        await q.edit_message_text(txt, reply_markup=_kb_settings_sub(ui, st2["append_tr"]))
        await q.answer("✅")
        return

    # ---------- apply specific choices ----------
    if data.startswith(f"{CB}SET:LANG:"):
        code = data.split(":", 3)[-1]
        # в активную сессию
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

    # если что-то неизвестное
    await q.answer()
