from __future__ import annotations
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from state.session import user_sessions
from components.profile_db import save_user_profile
from components.i18n import get_ui_lang

# две опции: casual / business
def _kb_styles(ui: str) -> InlineKeyboardMarkup:
    if ui == "ru":
        btns = [
            InlineKeyboardButton("😎 Разговорный", callback_data="CMD:STYLE:casual"),
            InlineKeyboardButton("🤓 Деловой",     callback_data="CMD:STYLE:business"),
        ]
    else:
        btns = [
            InlineKeyboardButton("😎 Casual",   callback_data="CMD:STYLE:casual"),
            InlineKeyboardButton("🤓 Business", callback_data="CMD:STYLE:business"),
        ]
    return InlineKeyboardMarkup([btns])

async def style_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, ctx)
    prompt = "Выбери стиль общения:" if ui == "ru" else "Choose your conversation style:"
    await update.effective_message.reply_text(prompt, reply_markup=_kb_styles(ui))

async def style_on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    parts = (q.data or "").split(":", 2)
    if len(parts) != 3:
        return
    _, _, style = parts
    chat_id = q.message.chat_id

    sess = user_sessions.setdefault(chat_id, {})
    sess["style"] = style
    try:
        save_user_profile(chat_id, style=style)
    except Exception:
        pass

    ui = get_ui_lang(update, ctx)
    if ui == "ru":
        label = "Разговорный" if style == "casual" else "Деловой"
        await q.edit_message_text(f"Готово! Стиль: {label}")
    else:
        label = "Casual" if style == "casual" else "Business"
        await q.edit_message_text(f"Done! Style: {label}")
