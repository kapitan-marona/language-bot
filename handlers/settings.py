from __future__ import annotations
from typing import List, Tuple
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from components.profile_db import get_user_profile, save_user_profile
from components.promo import restrict_target_languages_if_needed, is_promo_valid
from components.i18n import get_ui_lang
from state.session import user_sessions

# Переводчик (для входа по кнопке)
from handlers.translator_mode import enter_translator, exit_translator, ensure_tr_defaults  # type: ignore

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

# Уровни
LEVELS_ROW1 = ["A0", "A1", "A2", "B1"]
LEVELS_ROW2 = ["B2", "C1", "C2"]

STYLE_TITLES = {
    "casual":   {"ru": "😎 Разговорный", "en": "😎 Casual"},
    "business": {"ru": "🤓 Деловой",     "en": "🤓 Business"},
}
STYLE_ORDER = ["casual", "business"]


# -------------------- helpers --------------------

def _name_for_lang(code: str) -> str:
    for title, c in LANGS:
        if c == code:
            return title
    return code

def _name_for_style(code: str, ui: str) -> str:
    d = STYLE_TITLES.get(code, {})
    return d.get(ui, d.get("ru", code))

def _get_state(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Единый снимок настроек: profile_db + user_sessions."""
    prof = get_user_profile(chat_id) or {}
    sess = user_sessions.setdefault(chat_id, {})

    ui = sess.get("interface_lang") or prof.get("interface_lang") or get_ui_lang(None, context)  # type: ignore
    # target language
    tgt = (sess.get("target_lang") or prof.get("target_lang") or "en")
    level = (sess.get("level") or prof.get("level") or "B1")
    style = (sess.get("style") or prof.get("style") or "casual")

    # ответ: voice/text (в твоём коде используется sess["mode"])
    out_mode = sess.get("mode") or "text"

    # task_mode: chat/translator
    task_mode = sess.get("task_mode") or "chat"

    # дублирование (по твоей текущей логике — актуально для A0/A1)
    append_tr = bool(prof.get("append_translation")) if level in ("A0", "A1") else False

    english_only_note = (prof.get("promo_type") == "english_only" and is_promo_valid(prof))

    return {
        "ui": ui if ui in ("ru", "en") else "en",
        "tgt": tgt,
        "level": level,
        "style": style,
        "out_mode": out_mode if out_mode in ("text", "voice") else "text",
        "task_mode": task_mode if task_mode in ("chat", "translator") else "chat",
        "append_tr": append_tr,
        "english_only_note": english_only_note,
        "prof": prof,
        "sess": sess,
    }

def _main_text(ui: str, lang_name: str, level: str, style_name: str, out_mode: str, task_mode: str, append_tr: bool, english_only_note: bool) -> str:
    out_title = ("Аудио" if ui == "ru" else "Voice") if out_mode == "voice" else ("Текст" if ui == "ru" else "Text")
    mode_title = ("Переводчик" if ui == "ru" else "Translator") if task_mode == "translator" else ("Диалог" if ui == "ru" else "Chat")

    base_ru = (
        "⚙️ Настройки\n\n"
        f"• Язык: {lang_name}\n"
        f"• Уровень: {level}\n"
        f"• Стиль: {style_name}\n"
        f"• Формат ответа: {out_title}\n"
        f"• Режим: {mode_title}\n"
        f"• Дублирование: {'Вкл' if append_tr else 'Выкл'}\n\n"
        "Что хочешь поменять?"
    )
    base_en = (
        "⚙️ Settings\n\n"
        f"• Language: {lang_name}\n"
        f"• Level: {level}\n"
        f"• Style: {style_name}\n"
        f"• Reply format: {out_title}\n"
        f"• Mode: {mode_title}\n"
        f"• Native duplicates: {'On' if append_tr else 'Off'}\n\n"
        "What do you want to change?"
    )
    text = base_ru if ui == "ru" else base_en
    if english_only_note:
        text += (
            "\n\n❗ Промокод бессрочный, действует только для английского языка"
            if ui == "ru"
            else "\n\n❗ Promo is permanent and limits learning to English only"
        )
    return text

def _kb_main(ui: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✍️/🎙 Формат ответа" if ui == "ru" else "✍️/🎙 Reply format", callback_data="S:OPEN:FORMAT"),
        ],
        [
            InlineKeyboardButton("💬/🌍 Режим: диалог/переводчик" if ui == "ru" else "💬/🌍 Mode: chat/translator", callback_data="S:OPEN:MODE"),
        ],
        [
            InlineKeyboardButton("🛠 Настройки" if ui == "ru" else "🛠 Settings", callback_data="S:OPEN:SETTINGS"),
        ],
        [
            InlineKeyboardButton("⭐ Премиум" if ui == "ru" else "⭐ Premium", callback_data="S:OPEN:PREMIUM"),
        ],
    ])

def _kb_back(ui: str, to: str = "MAIN") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data=f"S:BACK:{to}")]
    ])

def _kb_format(ui: str, current: str) -> InlineKeyboardMarkup:
    t = "✅ Текст" if ui == "ru" else "✅ Text"
    v = "✅ Аудио" if ui == "ru" else "✅ Voice"
    btn_text = t if current == "text" else ("Текст" if ui == "ru" else "Text")
    btn_voice = v if current == "voice" else ("Аудио" if ui == "ru" else "Voice")
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(btn_text, callback_data="S:FORMAT:text"),
            InlineKeyboardButton(btn_voice, callback_data="S:FORMAT:voice"),
        ],
        [InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:BACK:MAIN")]
    ])

def _kb_mode(ui: str, current: str) -> InlineKeyboardMarkup:
    btn_chat = ("✅ Диалог" if ui == "ru" else "✅ Chat") if current == "chat" else ("Диалог" if ui == "ru" else "Chat")
    btn_tr = ("✅ Переводчик" if ui == "ru" else "✅ Translator") if current == "translator" else ("Переводчик" if ui == "ru" else "Translator")
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(btn_chat, callback_data="S:MODE:chat"),
            InlineKeyboardButton(btn_tr, callback_data="S:MODE:translator"),
        ],
        [InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:BACK:MAIN")]
    ])

def _kb_settings(ui: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Язык" if ui == "ru" else "Language", callback_data="S:OPEN:LANG"),
            InlineKeyboardButton("Уровень" if ui == "ru" else "Level", callback_data="S:OPEN:LEVEL"),
        ],
        [
            InlineKeyboardButton("Стиль" if ui == "ru" else "Style", callback_data="S:OPEN:STYLE"),
        ],
        [
            InlineKeyboardButton("Дублирование" if ui == "ru" else "Duplicates", callback_data="S:OPEN:DUP"),
        ],
        [InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:BACK:MAIN")]
    ])

def _langs_keyboard(chat_id: int, ui: str) -> InlineKeyboardMarkup:
    prof = get_user_profile(chat_id) or {}
    lang_map = {code: title for title, code in LANGS}
    lang_map = restrict_target_languages_if_needed(prof, lang_map)
    items = [(title, code) for code, title in lang_map.items()]

    rows = []
    for i in range(0, len(items), 2):
        chunk = items[i:i+2]
        rows.append([InlineKeyboardButton(t, callback_data=f"S:LANG:{c}") for (t, c) in chunk])

    rows.append([InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:BACK:SETTINGS")])
    return InlineKeyboardMarkup(rows)

def _levels_keyboard(ui: str) -> InlineKeyboardMarkup:
    row1 = [InlineKeyboardButton(x, callback_data=f"S:LEVEL:{x}") for x in LEVELS_ROW1]
    row2 = [InlineKeyboardButton(x, callback_data=f"S:LEVEL:{x}") for x in LEVELS_ROW2]
    back = [InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:BACK:SETTINGS")]
    return InlineKeyboardMarkup([row1, row2, back])

def _styles_keyboard(ui: str) -> InlineKeyboardMarkup:
    rows = []
    for code in STYLE_ORDER:
        title = _name_for_style(code, ui)
        rows.append([InlineKeyboardButton(title, callback_data=f"S:STYLE:{code}")])
    rows.append([InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:BACK:SETTINGS")])
    return InlineKeyboardMarkup(rows)

def _kb_duplicates(ui: str, enabled: bool, level: str) -> InlineKeyboardMarkup:
    # По твоей логике — включаем только A0/A1. На остальных — показываем, но делаем понятное сообщение.
    if level in ("A0", "A1"):
        label = ("✅ Вкл" if ui == "ru" else "✅ On") if enabled else ("❌ Выкл" if ui == "ru" else "❌ Off")
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(label, callback_data="S:DUP:TOGGLE")],
            [InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:BACK:SETTINGS")]
        ])
    else:
        msg = "Доступно только для A0–A1" if ui == "ru" else "Available for A0–A1 only"
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(msg, callback_data="S:DUP:INFO")],
            [InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:BACK:SETTINGS")]
        ])

def _kb_premium(ui: str) -> InlineKeyboardMarkup:
    # "Как оплатить" — через существующий htp_start (у тебя уже есть handler)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Купить" if ui == "ru" else "Buy", callback_data="S:PREM:BUY"),
            InlineKeyboardButton("Донат" if ui == "ru" else "Donate", callback_data="S:PREM:DONATE"),
        ],
        [
            InlineKeyboardButton("Как оплатить" if ui == "ru" else "How to pay", callback_data="htp_start"),
        ],
        [InlineKeyboardButton("⬅️ Назад" if ui == "ru" else "⬅️ Back", callback_data="S:BACK:MAIN")]
    ])


async def _edit_or_send(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, kb: InlineKeyboardMarkup):
    q = getattr(update, "callback_query", None)
    if q and q.message:
        await q.edit_message_text(text=text, reply_markup=kb)
        try:
            await q.answer()
        except Exception:
            pass
        return
    await context.bot.send_message(update.effective_chat.id, text, reply_markup=kb)


# -------------------- public: commands --------------------

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    st = _get_state(chat_id, context)

    text = _main_text(
        st["ui"],
        _name_for_lang(st["tgt"]),
        st["level"],
        _name_for_style(st["style"], st["ui"]),
        st["out_mode"],
        st["task_mode"],
        st["append_tr"],
        st["english_only_note"],
    )
    await _edit_or_send(update, context, text, _kb_main(st["ui"]))

# Алиасы (команды из меню Telegram)
async def cmd_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    st = _get_state(chat_id, context)
    sess = st["sess"]
    sess["mode"] = "voice"
    msg = "🎙 Теперь отвечаю голосом." if st["ui"] == "ru" else "🎙 Now I reply with voice."
    await update.effective_message.reply_text(msg)

async def cmd_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    st = _get_state(chat_id, context)
    sess = st["sess"]
    sess["mode"] = "text"
    msg = "⌨️ Теперь отвечаю текстом." if st["ui"] == "ru" else "⌨️ Now I reply with text."
    await update.effective_message.reply_text(msg)

async def cmd_translation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    st = _get_state(chat_id, context)
    sess = st["sess"]
    # Вход в режим переводчика (покажет инструкцию + одну кнопку направления внутри)
    await enter_translator(update, context, sess)

async def cmd_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    st = _get_state(chat_id, context)
    sess = st["sess"]
    await exit_translator(update, context, sess)


# -------------------- callbacks --------------------

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.data:
        return

    data = q.data
    chat_id = q.message.chat.id
    st = _get_state(chat_id, context)
    ui = st["ui"]
    sess = st["sess"]
    prof = st["prof"]

    # --- поддержка старых префиксов (чтобы во время теста ничего не ломать) ---
    # если прилетели SETTINGS:/SET: — просто откроем новое /settings
    if data.startswith("SETTINGS:") or data.startswith("SET:"):
        await cmd_settings(update, context)
        return

    # -------------------- BACK --------------------
    if data.startswith("S:BACK:"):
        to = data.split(":", 2)[-1]
        if to == "MAIN":
            await cmd_settings(update, context)
            return
        if to == "SETTINGS":
            text = "🛠 Настройки" if ui == "ru" else "🛠 Settings"
            await _edit_or_send(update, context, text, _kb_settings(ui))
            return
        # fallback
        await cmd_settings(update, context)
        return

    # -------------------- OPEN screens --------------------
    if data == "S:OPEN:FORMAT":
        text = "Выбери формат ответа:" if ui == "ru" else "Choose reply format:"
        await _edit_or_send(update, context, text, _kb_format(ui, st["out_mode"]))
        return

    if data == "S:OPEN:MODE":
        text = "Выбери режим:" if ui == "ru" else "Choose mode:"
        await _edit_or_send(update, context, text, _kb_mode(ui, st["task_mode"]))
        return

    if data == "S:OPEN:SETTINGS":
        text = "🛠 Настройки" if ui == "ru" else "🛠 Settings"
        await _edit_or_send(update, context, text, _kb_settings(ui))
        return

    if data == "S:OPEN:PREMIUM":
        text = "⭐ Премиум" if ui == "ru" else "⭐ Premium"
        await _edit_or_send(update, context, text, _kb_premium(ui))
        return

    if data == "S:OPEN:LANG":
        text = "Выбери язык:" if ui == "ru" else "Choose a language:"
        await _edit_or_send(update, context, text, _langs_keyboard(chat_id, ui))
        return

    if data == "S:OPEN:LEVEL":
        text = "Выбери уровень:" if ui == "ru" else "Choose your level:"
        await _edit_or_send(update, context, text, _levels_keyboard(ui))
        return

    if data == "S:OPEN:STYLE":
        text = "Выбери стиль:" if ui == "ru" else "Choose style:"
        await _edit_or_send(update, context, text, _styles_keyboard(ui))
        return

    if data == "S:OPEN:DUP":
        level = st["level"]
        enabled = bool(prof.get("append_translation")) if level in ("A0", "A1") else False
        text = (
            "Дублирование на языке интерфейса (A0–A1):"
            if ui == "ru" else
            "Native duplicates (A0–A1):"
        )
        await _edit_or_send(update, context, text, _kb_duplicates(ui, enabled, level))
        return

    # -------------------- APPLY format/mode --------------------
    if data.startswith("S:FORMAT:"):
        val = data.split(":", 2)[-1]
        sess["mode"] = "voice" if val == "voice" else "text"
        text = "Выбери формат ответа:" if ui == "ru" else "Choose reply format:"
        await _edit_or_send(update, context, text, _kb_format(ui, sess["mode"]))
        return

    if data.startswith("S:MODE:"):
        val = data.split(":", 2)[-1]
        if val == "translator":
            # сразу входим и показываем инструкцию/кнопку направления в переводчике
            await enter_translator(update, context, sess)
            return
        else:
            # chat
            sess["task_mode"] = "chat"
            msg = "💬 Режим диалога включён." if ui == "ru" else "💬 Chat mode is ON."
            await q.answer("✅")
            await context.bot.send_message(chat_id, msg)
            return

    # -------------------- SETTINGS values --------------------
    if data.startswith("S:LANG:"):
        code = data.split(":", 2)[-1]
        sess["target_lang"] = code
        try:
            save_user_profile(chat_id, target_lang=code)
        except Exception:
            logger.debug("save_user_profile(target_lang) failed", exc_info=True)
        await q.answer("✅")
        # возвращаемся в общий /settings
        await cmd_settings(update, context)
        return

    if data.startswith("S:LEVEL:"):
        level = data.split(":", 2)[-1]
        sess["level"] = level
        try:
            save_user_profile(chat_id, level=level)
        except Exception:
            logger.debug("save_user_profile(level) failed", exc_info=True)
        await q.answer("✅")
        await cmd_settings(update, context)
        return

    if data.startswith("S:STYLE:"):
        style = data.split(":", 2)[-1]
        sess["style"] = style
        try:
            save_user_profile(chat_id, style=style)
        except Exception:
            logger.debug("save_user_profile(style) failed", exc_info=True)
        await q.answer("✅")
        await cmd_settings(update, context)
        return

    # duplicates
    if data == "S:DUP:TOGGLE":
        level = st["level"]
        if level in ("A0", "A1"):
            new_val = not bool(prof.get("append_translation"))
            try:
                save_user_profile(chat_id, append_translation=new_val, append_translation_lang=(prof.get("interface_lang") or "en"))
            except Exception:
                logger.debug("save_user_profile(append_translation) failed", exc_info=True)
            await q.answer("✅")
            await cmd_settings(update, context)
            return
        await q.answer("Недоступно" if ui == "ru" else "Unavailable", show_alert=True)
        return

    if data == "S:DUP:INFO":
        await q.answer("Доступно только для A0–A1" if ui == "ru" else "Available for A0–A1 only", show_alert=True)
        return

    # -------------------- PREMIUM actions --------------------
    if data == "S:PREM:BUY":
        await q.answer("⭐")
        try:
            from handlers.commands.payments import buy_command
            await buy_command(update, context)
        except Exception:
            logger.exception("buy_command failed")
        return

    if data == "S:PREM:DONATE":
        await q.answer("❤️")
        try:
            from handlers.commands.donate import donate_command
            await donate_command(update, context)
        except Exception:
            logger.exception("donate_command failed")
        return

    # fallback
    logger.warning("Unhandled settings callback: %r", data)
    try:
        await q.answer()
    except Exception:
        pass
