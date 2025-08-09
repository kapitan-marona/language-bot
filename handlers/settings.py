# handlers/settings.py
from __future__ import annotations
from typing import Dict, List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from components.profile_db import get_user_profile, save_user_profile
from handlers.chat.levels_text import get_level_guide  # ← используем тот же гайд, что и в онбординге

# ===== Локализация UI-текстов =====
UI = {
    "ru": {
        "menu": "Что хочешь поменять?",
        "change_lang": "🛠️ Поменять язык",
        "change_level": "🛠️ Поменять уровень",
        "change_style": "🛠️ Поменять стиль",
        "pick_level": "Выбери уровень:",
        "pick_lang": "Выбери язык:",
        "pick_style": "Выбери стиль общения:",
        "back": "👈 Назад",
        "current": "Текущие настройки:",
        "lang_label": "• Язык",
        "level_label": "• Уровень",
        "style_label": "• Стиль общения",
        "confirm": "Готово! {field} → {value}. Остальные настройки без изменений.",
        "field_map": {"language": "Язык", "level": "Уровень", "style": "Стиль"},
        "style_map": {"casual": "Разговорный", "business": "Деловой"},
    },
    "en": {
        "menu": "What would you like to change?",
        "change_lang": "🛠️ Change language",
        "change_level": "🛠️ Change level",
        "change_style": "🛠️ Change style",
        "pick_level": "Pick a level:",
        "pick_lang": "Pick a language:",
        "pick_style": "Pick a style:",
        "back": "👈 Back",
        "current": "Current settings:",
        "lang_label": "• Language",
        "level_label": "• Level",
        "style_label": "• Style",
        "confirm": "Done! {field} → {value}. Other settings unchanged.",
        "field_map": {"language": "Language", "level": "Level", "style": "Style"},
        "style_map": {"casual": "Casual", "business": "Business"},
    },
}

def _t(s: Dict) -> dict:
    return UI.get(s.get("ui_lang", "ru"), UI["ru"])

# ===== Дефолты и перечни =====
DEFAULTS = {"ui_lang": "ru", "language": "en", "style": "casual", "level": "B1"}

# Только эти языки, как ты просила (с флагами и отображаемыми названиями)
LANGS: List[Tuple[str, str]] = [
    ("🇷🇺 Русский", "ru"),
    ("🇬🇧 English", "en"),
    ("🇫🇷 Français", "fr"),
    ("🇪🇸 Español", "es"),
    ("🇩🇪 Deutsch", "de"),
    ("🇸🇪 Svenska", "sv"),
    ("🇫🇮 Suomi", "fi"),
]

# Порядок уровней как в онбординге
LEVELS: List[str] = ["A0", "A1", "A2", "B1", "B2", "C1", "C2"]

# Два стиля (эмодзи стоят СПРАВА от текста)
STYLES: List[Tuple[str, str]] = [("Разговорный", "casual"), ("Деловой", "business")]

# ===== Сессия (синхронизация с БД по chat_id) =====
def get_session(context: ContextTypes.DEFAULT_TYPE, chat_id: int | None = None) -> Dict:
    ud = context.user_data
    if chat_id is not None:
        prof = get_user_profile(chat_id) or {}
        ud.update({
            "ui_lang": prof.get("interface_lang", DEFAULTS["ui_lang"]),
            "language": prof.get("target_lang", DEFAULTS["language"]),
            "level": prof.get("level", DEFAULTS["level"]),
            "style": prof.get("style", DEFAULTS["style"]),
        })
    for k, v in DEFAULTS.items():
        ud.setdefault(k, v)
    return ud

# ===== Утилита для разбиения на строки по N кнопок =====
def _chunk(seq, n=2):
    return [seq[i:i+n] for i in range(0, len(seq), n)]

# ===== Клавиатуры =====
def build_settings_menu(session: Dict) -> InlineKeyboardMarkup:
    t = _t(session)
    kb = [
        [InlineKeyboardButton(t["change_lang"],  callback_data="SETTINGS:LANG")],
        [InlineKeyboardButton(t["change_level"], callback_data="SETTINGS:LEVEL")],
        [InlineKeyboardButton(t["change_style"], callback_data="SETTINGS:STYLE")],
    ]
    return InlineKeyboardMarkup(kb)

def build_language_kb(session: Dict) -> InlineKeyboardMarkup:
    t = _t(session)
    buttons = [InlineKeyboardButton(name, callback_data=f"SET:language:{code}") for name, code in LANGS]
    # по 2 кнопки в строке
    rows = _chunk(buttons, n=2)
    rows = [[*row] for row in rows]
    rows.append([InlineKeyboardButton(t["back"], callback_data="SETTINGS:MENU")])
    return InlineKeyboardMarkup(rows)

def build_level_kb(session: Dict) -> InlineKeyboardMarkup:
    t = _t(session)
    # Без эмодзи; раскладка как в онбординге:
    # 1 строка: A0 A1 A2
    # 2 строка: B1 B2 C1 C2
    row1 = [InlineKeyboardButton(lv, callback_data=f"SET:level:{lv}") for lv in ["A0", "A1", "A2"]]
    row2 = [InlineKeyboardButton(lv, callback_data=f"SET:level:{lv}") for lv in ["B1", "B2", "C1", "C2"]]
    rows = [row1, row2, [InlineKeyboardButton(t["back"], callback_data="SETTINGS:MENU")]]
    return InlineKeyboardMarkup(rows)

def build_style_kb(session: Dict) -> InlineKeyboardMarkup:
    t = _t(session)
    # Эмодзи справа: "Разговорный 😎" / "Деловой 🤓"
    labels_ru = {"casual": "Разговорный 😎", "business": "Деловой 🤓"}
    labels_en = {"casual": "Casual 😎", "business": "Business 🤓"}
    labels = labels_ru if session.get("ui_lang", "ru") == "ru" else labels_en

    buttons = [
        InlineKeyboardButton(labels[code], callback_data=f"SET:style:{code}")
        for _, code in STYLES
    ]
    # по 2 в строке
    rows = _chunk(buttons, n=2)
    rows = [[*row] for row in rows]
    rows.append([InlineKeyboardButton(t["back"], callback_data="SETTINGS:MENU")])
    return InlineKeyboardMarkup(rows)

# ===== Форматирование заголовка =====
def format_settings_header(s: Dict) -> str:
    t = _t(s)
    lang_map = {code: name for name, code in LANGS}  # code -> "🇬🇧 English"
    language_name = lang_map.get(s.get("language", "en"), s.get("language", "en"))
    style_name = t["style_map"].get(s.get("style", "casual"), s.get("style", "casual"))
    level = s.get("level", "B1")
    return (
        f"{t['current']}\n"
        f"{t['lang_label']}: {language_name}\n"
        f"{t['level_label']}: {level}\n"
        f"{t['style_label']}: {style_name}\n\n"
        f"{t['menu']}"
    )

# ===== Команды/колбэки =====
async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id if update and update.effective_chat else None
    s = get_session(context, chat_id)
    text = format_settings_header(s)
    if update.message:
        await update.message.reply_text(text, reply_markup=build_settings_menu(s))
    else:
        await update.effective_chat.send_message(text, reply_markup=build_settings_menu(s))

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()
    data = q.data or ""

    chat_id = update.effective_chat.id if update and update.effective_chat else None
    s = get_session(context, chat_id)
    t = _t(s)

    if data == "SETTINGS:MENU":
        return await q.edit_message_text(format_settings_header(s), reply_markup=build_settings_menu(s))

    if data == "SETTINGS:LEVEL":
        # Покажем выбор + гайд из онбординга, чтобы тексты и эмодзи совпадали
        guide = get_level_guide(s.get("ui_lang", "ru"))
        return await q.edit_message_text(f"{t['pick_level']}\n\n{guide}", parse_mode="Markdown", reply_markup=build_level_kb(s))

    if data == "SETTINGS:LANG":
        return await q.edit_message_text(t["pick_lang"], reply_markup=build_language_kb(s))

    if data == "SETTINGS:STYLE":
        return await q.edit_message_text(t["pick_style"], reply_markup=build_style_kb(s))

    if data.startswith("SET:"):
        try:
            _, field, value = data.split(":", 2)
        except ValueError:
            return

        s[field] = value  # обновляем выбранное поле

        # сохраняем в БД по chat_id
        if chat_id is not None:
            try:
                save_user_profile(
                    chat_id,
                    interface_lang=s.get("ui_lang"),
                    target_lang=s.get("language"),
                    level=s.get("level"),
                    style=s.get("style"),
                )
            except Exception:
                pass

        field_h = t["field_map"].get(field, field)
        confirm = t["confirm"].format(field=field_h, value=value)
        await q.edit_message_text(confirm + "\n\n" + format_settings_header(s), reply_markup=build_settings_menu(s))

def register_settings_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CallbackQueryHandler(on_callback, pattern=r"^(SETTINGS|SET):"))
