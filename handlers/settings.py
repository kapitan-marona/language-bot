"""
handlers/settings.py

Панель настроек пользователя для Telegram-бота на python-telegram-bot v20.

Функционал:
- /settings — показать текущее состояние и меню изменения настроек
- Кнопки: «Поменять язык», «Поменять уровень», «Поменять стиль»
- Переиспользуемые клавиатуры уровней/языков/стилей
- Единый обработчик CallbackQuery с компактным протоколом callback_data

Зависимости: python-telegram-bot >= 20
Интеграция: см. функцию register_settings_handlers(app)
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

DEFAULTS = {
    "ui_lang": "ru",
    "language": "en",
    "style": "casual",
    "level": "B1",
}

LEVELS: List[str] = ["A0", "A1", "A2", "B1", "B2", "C1", "C2"]
LANGS: List[Tuple[str, str]] = [
    ("English", "en"),
    ("Español", "es"),
    ("Deutsch", "de"),
]
STYLES: List[Tuple[str, str]] = [
    ("Разговорный", "casual"),
    ("Деловой", "business"),
]

LEVEL_GUIDE = (
    "\n".join(
        [
            "Гайд по уровням (кратко):",
            "A0–A1: базовые фразы, алфавит, простые вопросы",
            "A2: повседневные темы, короткие диалоги",
            "B1: уверенный бытовой разговор, путешествия",
            "B2: рабочие темы, сложнее грамматика",
            "C1–C2: продвинутые дискуссии, нюансы стиля",
        ]
    )
)

def get_session(context: ContextTypes.DEFAULT_TYPE) -> Dict:
    ud = context.user_data
    for k, v in DEFAULTS.items():
        ud.setdefault(k, v)
    return ud

def build_settings_menu(session: Dict) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton("Поменять язык", callback_data="SETTINGS:LANG")],
        [InlineKeyboardButton("Поменять уровень", callback_data="SETTINGS:LEVEL")],
        [InlineKeyboardButton("Поменять стиль", callback_data="SETTINGS:STYLE")],
    ]
    return InlineKeyboardMarkup(kb)

def build_level_kb() -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton(lv, callback_data=f"SET:level:{lv}")] for lv in LEVELS
    ]
    rows.append([InlineKeyboardButton("« Назад", callback_data="SETTINGS:MENU")])
    return InlineKeyboardMarkup(rows)

def build_language_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(name, callback_data=f"SET:language:{code}")]
        for name, code in LANGS
    ]
    rows.append([InlineKeyboardButton("« Назад", callback_data="SETTINGS:MENU")])
    return InlineKeyboardMarkup(rows)

def build_style_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(name, callback_data=f"SET:style:{code}")]
        for name, code in STYLES
    ]
    rows.append([InlineKeyboardButton("« Назад", callback_data="SETTINGS:MENU")])
    return InlineKeyboardMarkup(rows)

def format_settings_header(s: Dict) -> str:
    lang_map = {code: name for name, code in LANGS}
    style_map = {
        "casual": "Разговорный",
        "business": "Деловой",
    }
    language_name = lang_map.get(s.get("language", "en"), s.get("language", "en"))
    style_name = style_map.get(s.get("style", "casual"), s.get("style", "casual"))
    level = s.get("level", "B1")
    header = (
        f"Текущие настройки (активные параметры обучения):\n"
        f"• Язык: {language_name} — на котором ты сейчас учишься\n"
        f"• Уровень: {level} — твой текущий уровень владения языком\n"
        f"• Стиль общения: {style_name} — формат подачи материала и диалога\n\n"
        f"Что хочешь поменять?"
    )
    return header

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = get_session(context)
    text = format_settings_header(s)
    if update.message:
        await update.message.reply_text(text, reply_markup=build_settings_menu(s))
    else:
        await update.effective_chat.send_message(text, reply_markup=build_settings_menu(s))

async def cmd_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Выбери уровень (ориентируйся на гайд ниже):\n\n" + LEVEL_GUIDE,
        reply_markup=build_level_kb(),
    )

async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Выбери язык:", reply_markup=build_language_kb())

async def cmd_style(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Выбери стиль общения:", reply_markup=build_style_kb())

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()
    data = q.data or ""
    if data == "SETTINGS:MENU":
        s = get_session(context)
        return await q.edit_message_text(
            format_settings_header(s), reply_markup=build_settings_menu(s)
        )
    if data == "SETTINGS:LEVEL":
        return await q.edit_message_text(
            "Выбери уровень (ориентируйся на гайд ниже):\n\n" + LEVEL_GUIDE,
            reply_markup=build_level_kb(),
        )
    if data == "SETTINGS:LANG":
        return await q.edit_message_text(
            "Выбери язык:", reply_markup=build_language_kb()
        )
    if data == "SETTINGS:STYLE":
        return await q.edit_message_text(
            "Выбери стиль общения:", reply_markup=build_style_kb()
        )
    if data.startswith("SET:"):
        try:
            _, field, value = data.split(":", 2)
        except ValueError:
            return
        s = get_session(context)
        s[field] = value
        confirm_field_map = {
            "language": "Язык",
            "level": "Уровень",
            "style": "Стиль",
        }
        human_field = confirm_field_map.get(field, field)
        confirm = f"Готово! {human_field} → {value}. Остальные настройки без изменений."
        await q.edit_message_text(
            confirm + "\n\n" + format_settings_header(s),
            reply_markup=build_settings_menu(s),
        )

def register_settings_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CommandHandler("level", cmd_level))
    app.add_handler(CommandHandler("language", cmd_language))
    app.add_handler(CommandHandler("style", cmd_style))
    app.add_handler(CallbackQueryHandler(on_callback, pattern=r"^(SETTINGS|SET):"))
