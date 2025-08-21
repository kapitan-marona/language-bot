from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from utils.decorators import safe_handler
from state.session import user_sessions
from components.profile_db import save_user_profile
from components.i18n import get_ui_lang

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# /teach — вкл/выкл режим «объясняй и тренируй»
# Использование:
#   /teach           → показать состояние и краткую помощь
#   /teach on        → включить режим
#   /teach off       → выключить режим
# Влияет на системный промпт через флаг в сессии (если он учитывается в prompt).
# ────────────────────────────────────────────────────────────────────────────────

@safe_handler
async def teach_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ui = get_ui_lang(update, context)
    session = user_sessions.setdefault(chat_id, {})

    arg = (context.args[0].lower() if context.args else "").strip()

    if arg in {"on", "true", "1"}:
        session["teach_enabled"] = True
        msg = ("Режим тренера включён. Буду чаще объяснять правила и давать мини-упражнения. "
               "Чтобы выключить, напиши /teach off."
               if ui == "ru" else
               "Teach mode is ON. I’ll explain rules more and give mini-drills. "
               "To turn off, use /teach off.")
        await update.effective_message.reply_text(msg)
        return

    if arg in {"off", "false", "0"}:
        session["teach_enabled"] = False
        msg = ("Режим тренера выключен. Чтобы включить снова — /teach on."
               if ui == "ru" else
               "Teach mode is OFF. To enable again — /teach on.")
        await update.effective_message.reply_text(msg)
        return

    # Показать текущее состояние + помощь
    current = session.get("teach_enabled", False)
    if ui == "ru":
        await update.effective_message.reply_text(
            "Режим тренера: " + ("включён ✅" if current else "выключен ⛔️") +
            "\n\nКоманды:\n• /teach on — включить\n• /teach off — выключить\n• /glossary — мини-глоссарий по нашей беседе"
        )
    else:
        await update.effective_message.reply_text(
            "Teach mode: " + ("ON ✅" if current else "OFF ⛔️") +
            "\n\nCommands:\n• /teach on — enable\n• /teach off — disable\n• /glossary — a small glossary for our chat"
        )

def build_teach_handler() -> CommandHandler:
    # Возвращаем обычный CommandHandler (без block/group — это задаётся снаружи)
    return CommandHandler("teach", teach_command)

# ────────────────────────────────────────────────────────────────────────────────
# /glossary — в будущем может собирать термины из сессии; сейчас — подсказка
# ────────────────────────────────────────────────────────────────────────────────
@safe_handler
async def glossary_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, context)
    if ui == "ru":
        await update.effective_message.reply_text(
            "Пока глоссарий показывает только подсказку. Попроси Мэтта: "
            "«Сделай мини-глоссарий по нашей беседе» — он соберёт важные слова и примеры. "
            "Можно уточнить тему: «…по теме путешествий»."
        )
    else:
        await update.effective_message.reply_text(
            "Glossary is a tip for now. Ask Matt: "
            "“Make a mini-glossary for our chat” — he’ll collect key words and examples. "
            "You can specify a topic, e.g., “...about travel”."
        )

# ────────────────────────────────────────────────────────────────────────────────
# /consent_on /consent_off — флажок согласия на обезличенное обучение (опционально)
# ────────────────────────────────────────────────────────────────────────────────
@safe_handler
async def consent_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ui = get_ui_lang(update, context)

    try:
        save_user_profile(chat_id, training_consent=True)
    except Exception:
        logger.exception("Failed to save training_consent=True for chat_id=%s", chat_id)

    if ui == "ru":
        await update.effective_message.reply_text(
            "Спасибо! Ты согласен(на) на обезличенное использование диалогов для улучшения качества. "
            "Можно отключить в любой момент: /consent_off."
        )
    else:
        await update.effective_message.reply_text(
            "Thanks! You consent to anonymized use of chats to improve quality. "
            "You can revoke it anytime: /consent_off."
        )

@safe_handler
async def consent_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ui = get_ui_lang(update, context)

    try:
        save_user_profile(chat_id, training_consent=False)
    except Exception:
        logger.exception("Failed to save training_consent=False for chat_id=%s", chat_id)

    if ui == "ru":
        await update.effective_message.reply_text(
            "Окей! Согласие отключено. Если захочешь вернуть — /consent_on."
        )
    else:
        await update.effective_message.reply_text(
            "Got it! Consent disabled. To enable again — /consent_on."
        )
