# handlers/commands/privacy.py
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from components.i18n import get_ui_lang

# --- ссылки ---
PRIVACY_LINKS = {
    "ru": "https://docs.google.com/document/d/1wv_vEGxH9ZxsYhYyl0ckJyKIaUlFU7KbgBzFoalZblg/edit?usp=sharing",
    "en": "https://docs.google.com/document/d/1Czelw_JYSHuRcKoIB1LzFBdL7e-hxd81M0YzaUMBl-w/edit?usp=sharing",
}

# --- текст ---
def _privacy_text(ui: str) -> str:
    if ui == "en":
        return (
            "🔒 <b>Privacy & data</b>\n\n"
            "The bot stores only technical data: your ID, settings, usage counters, and payment status. "
            "This is needed to keep the conversation flow and show limits.\n\n"
            "You can delete your data anytime with /delete_me.\n"
            f"Details: <a href='{PRIVACY_LINKS['en']}'>Privacy Policy</a>"
        )
    else:
        return (
            "🔒 <b>Конфиденциальность и данные</b>\n\n"
            "Бот хранит только технические данные: ваш ID, настройки, счётчики использования и статус оплат. "
            "Это нужно, чтобы помнить ваши предпочтения и поддерживать диалог.\n\n"
            "Вы можете удалить данные в любой момент командой /delete_me.\n"
            f"Подробнее: <a href='{PRIVACY_LINKS['ru']}'>Политика конфиденциальности</a>"
        )

async def privacy_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, ctx)
    await update.effective_message.reply_text(_privacy_text(ui), parse_mode="HTML")


# --- /delete_me (человечная формулировка) ---

async def delete_me_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, ctx)
    chat_id = update.effective_chat.id

    removed_total = 0

    def _try(module_path, fn_name="delete_user"):
        nonlocal removed_total
        try:
            mod = __import__(module_path, fromlist=[fn_name])
            fn = getattr(mod, fn_name)
            n = int(fn(chat_id) or 0)
            removed_total += n
        except Exception:
            pass

    _try("components.profile_db")
    _try("components.usage_db")
    _try("components.training_db")

    try:
        from state.session import user_sessions
        user_sessions.pop(chat_id, None)
    except Exception:
        pass

    if ui == "en":
        if removed_total > 0:
            msg = "✅ Your data has been deleted.\nThe bot has erased your profile and usage info."
        else:
            msg = "✅ No personal data found (or it was already removed)."
    else:
        if removed_total > 0:
            msg = "✅ Ваши данные удалены.\nБот стер информацию о профиле и использовании."
        else:
            msg = "✅ Персональных данных не найдено (или они уже удалены)."

    await update.effective_message.reply_text(msg)
