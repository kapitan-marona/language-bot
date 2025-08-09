"""
handlers/settings.py — Панель настроек пользователя (локализовано RU/EN по ui_lang).
Логика и структура сохранены, изменены только тексты и подписи кнопок.
"""
from __future__ import annotations
from typing import Dict, List, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from components.profile_db import get_user_profile, save_user_profile

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
        "back": "◀️ Назад",
        "current": "Текущие настройки:",
        "lang_label": "• Язык",
        "level_label": "• Уровень",
        "style_label": "• Стиль общения",
        "guide_title": "Гайд по уровням:",
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
        "back": "◀️ Back",
        "current": "Current settings:",
        "lang_label": "• Language",
        "level_label": "• Level",
        "style_label": "• Style",
        "guide_title": "Level guide:",
        "confirm": "Done! {field} → {value}. Other settings unchanged.",
        "field_map": {"language": "Language", "level": "Level", "style": "Style"},
        "style_map": {"casual": "Casual", "business": "Business"},
    },
}

def _t(s: Dict) -> dict:
    return UI.get(s.get("ui_lang", "ru"), UI["ru"])

# ===== Дефолты и перечни =====
DEFAULTS = {
    "ui_lang": "ru",
    "language": "en",
    "style": "casual",
    "level": "B1",
}

LEVELS: List[str] = ["A0", "A1", "A2", "B1", "B2", "C1", "C2"]
LANGS: List[Tuple[str, str]] = [("English", "en"), ("Español", "es"), ("Deutsch", "de")]
STYLES: List[Tuple[str, str]] = [("Разговорный", "casual"), ("Деловой", "business")]

LEVEL_GUIDE_RU = "\n".join([
    "Гайд по уровням:",
    "A0–A1: базовые фразы, алфавит, простые вопросы",
    "A2: повседневные темы, короткие диалоги",
    "B1: уверенный бытовой разговор, путешествия",
    "B2: рабочие темы, сложнее грамматика",
    "C1–C2: продвинутые дискуссии, нюансы стиля",
])
LEVEL_GUIDE_EN = "\n".join([
    "Level guide:",
    "A0–A1: alphabet, basic phrases, simple questions",
    "A2: everyday topics, short dialogues",
    "B1: confident daily talk, travel",
    "B2: work topics, more complex grammar",
    "C1–C2: advanced discussions, style nuances",
])

# ===== Сессия (синхронизация с БД) =====

def get_session(context: ContextTypes.DEFAULT_TYPE, user_id: int | None = None) -> Dict:
    ud = context.user_data
    if user_id is not None:
        try:
            prof = get_user_profile(user_id) or {}
        except Exception:
            prof = {}
        ud.update({
            "ui_lang": prof.get("interface_lang", DEFAULTS["ui_lang"]),
            "language": prof.get("target_lang", DEFAULTS["language"]),
            "level": prof.get("level", DEFAULTS["level"]),
            "style": prof.get("style", DEFAULTS["style"]),
        })
    for k, v in DEFAULTS.items():
        ud.setdefault(k, v)
    return ud

# ===== Клавиатуры =====

def build_settings_menu(session: Dict) -> InlineKeyboardMarkup:
    t = _t(session)
    kb = [
        [InlineKeyboardButton(t["change_lang"],  callback_data="SETTINGS:LANG")],
        [InlineKeyboardButton(t["change_level"], callback_data="SETTINGS:LEVEL")],
        [InlineKeyboardButton(t["change_style"], callback_data="SETTINGS:STYLE")],
    ]
    return InlineKeyboardMarkup(kb)


def build_level_kb(session: Dict) -> InlineKeyboardMarkup:
    t = _t(session)
    rows = [[InlineKeyboardButton(f"🎯 {lv}", callback_data=f"SET:level:{lv}")] for lv in LEVELS]
    rows.append([InlineKeyboardButton(t["back"], callback_data="SETTINGS:MENU")])
    return InlineKeyboardMarkup(rows)


def build_language_kb(session: Dict) -> InlineKeyboardMarkup:
    t = _t(session)
    rows = [[InlineKeyboardButton(("🇬🇧 " if code=="en" else "🇪🇸 " if code=="es" else "🇩🇪 ") + name,
                                  callback_data=f"SET:language:{code}")]
            for name, code in LANGS]
    rows.append([InlineKeyboardButton(t["back"], callback_data="SETTINGS:MENU")])
    return InlineKeyboardMarkup(rows)


def build_style_kb(session: Dict) -> InlineKeyboardMarkup:
    t = _t(session)
    rows = [[InlineKeyboardButton(("🙂 " if code=="casual" else "💼 ") + name,
                                  callback_data=f"SET:style:{code}")]
            for name, code in STYLES]
    rows.append([InlineKeyboardButton(t["back"], callback_data="SETTINGS:MENU")])
    return InlineKeyboardMarkup(rows)

# ===== Форматирование заголовка =====

def format_settings_header(s: Dict) -> str:
    t = _t(s)
    lang_map = {code: name for name, code in LANGS}
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
    user_id = update.effective_user.id if update and update.effective_user else None
    s = get_session(context, user_id)
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
    user_id = update.effective_user.id if update and update.effective_user else None

    # Получаем сессию и тексты
    s = get_session(context, user_id)
    t = _t(s)

    # Переходы меню
    if data == "SETTINGS:MENU":
        return await q.edit_message_text(format_settings_header(s), reply_markup=build_settings_menu(s))
    if data == "SETTINGS:LEVEL":
        guide = LEVEL_GUIDE_RU if s.get("ui_lang", "ru") == "ru" else LEVEL_GUIDE_EN
        guide = guide.replace("Гайд по уровням:", t["guide_title"]).replace("Level guide:", t["guide_title"])  # локализуем заголовок
        return await q.edit_message_text(f"{t['pick_level']}\n\n" + guide, reply_markup=build_level_kb(s))
    if data == "SETTINGS:LANG":
        return await q.edit_message_text(t["pick_lang"], reply_markup=build_language_kb(s))
    if data == "SETTINGS:STYLE":
        return await q.edit_message_text(t["pick_style"], reply_markup=build_style_kb(s))

    # Применение изменений
    if data.startswith("SET:"):
        try:
            _, field, value = data.split(":", 2)
        except ValueError:
            return
        s[field] = value
        if user_id is not None:
            try:
                save_user_profile(
                    user_id,
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
