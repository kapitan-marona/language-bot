# handlers/commands/privacy.py
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from components.i18n import get_ui_lang

# --- ТЕКСТ /privacy (RU/EN) ---

def _privacy_text(ui: str) -> str:
    if ui == "en":
        return (
            "🔒 <b>Privacy & data</b>\n\n"
            "<b>What I store</b>\n"
            "• your Telegram chat ID (to reply to you);\n"
            "• your learning settings (interface/target language, level, chat style);\n"
            "• usage counters (to show free limits);\n"
            "• payment status via Telegram Stars (no card data — payments are handled by Telegram).\n\n"
            "<b>Why</b>\n"
            "• to remember preferences and keep the conversation flow;\n"
            "• to show limits and process payments.\n\n"
            "<b>Where & how long</b>\n"
            "• stored in a managed cloud DB; access is limited to the bot owner;\n"
            "• we keep data while you use the bot or until you delete it.\n\n"
            "<b>Control</b>\n"
            "• use /delete_me to remove your data;\n"
            "• questions: @marrona.\n"
        )
    else:
        return (
            "🔒 <b>Конфиденциальность и данные</b>\n\n"
            "<b>Что я храню</b>\n"
            "• ваш Telegram chat ID (чтобы отвечать вам);\n"
            "• ваши учебные настройки (язык интерфейса/цели, уровень, стиль общения);\n"
            "• счётчики использования (чтобы показывать лимиты);\n"
            "• статус оплат через Telegram Stars (без данных карт — оплату ведёт Telegram).\n\n"
            "<b>Зачем</b>\n"
            "• чтобы помнить предпочтения и поддерживать контекст диалога;\n"
            "• чтобы показывать лимиты и обрабатывать оплаты.\n\n"
            "<b>Где и как долго</b>\n"
            "• в управляемой облачной БД, доступ есть только у владельца бота;\n"
            "• храним пока вы пользуетесь ботом или до вашего удаления.\n\n"
            "<b>Управление</b>\n"
            "• команда /delete_me удалит ваши данные;\n"
            "• вопросы: @marrona.\n"
        )

async def privacy_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, ctx)
    await update.effective_message.reply_text(_privacy_text(ui), parse_mode="HTML")


# --- /delete_me: удаляем данные пользователя из всех наших БД ---

async def delete_me_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, ctx)
    chat_id = update.effective_chat.id

    # Пытаемся вызвать delete_user в модулях БД. Если модуль или функция отсутствуют — просто пропускаем.
    removed_total = 0
    details = []

    def _try(module_path, fn_name="delete_user"):
        nonlocal removed_total, details
        try:
            mod = __import__(module_path, fromlist=[fn_name])
            fn = getattr(mod, fn_name)
            n = int(fn(chat_id) or 0)
            removed_total += n
            details.append(f"{module_path}: {n}")
        except Exception:
            # ничего не падает — просто считаем, что в этой БД нечего удалять/функции нет
            pass

    # Порядок: профили, usage, (опционально) training/glossary
    _try("components.profile_db")
    _try("components.usage_db")
    _try("components.training_db")  # если teach выключен — функции может не быть

    # Чистим временную сессию в памяти, если используете user_sessions
    try:
        from state.session import user_sessions
        user_sessions.pop(chat_id, None)
    except Exception:
        pass

    if ui == "en":
        if removed_total > 0:
            msg = "✅ Your data has been deleted."
        else:
            msg = "✅ No stored personal data found (or it was already removed)."
        tail = "\n\nDetails:\n" + "\n".join(details) if details else ""
        await update.effective_message.reply_text(msg + tail)
    else:
        if removed_total > 0:
            msg = "✅ Ваши данные удалены."
        else:
            msg = "✅ Персональных данных не найдено (или они уже удалены)."
        tail = "\n\nДетали:\n" + "\n".join(details) if details else ""
        await update.effective_message.reply_text(msg + tail)
