from __future__ import annotations
from typing import Dict, Any
from telegram import Update
from telegram.ext import ContextTypes

# ваш ин-мемори стор
from state.session import user_sessions  # dict-like: {chat_id: {...}}

# онбординг
from components.onboarding import send_onboarding  # отправляет привет и заводит этапы

# опционально: если есть ваш логгер
import logging
logger = logging.getLogger("english-bot")

# список возможных "флагов режима", которые иногда кладут в сессию
# если у вас другие ключи — добавьте сюда, лишнее удалять безопасно
RESET_KEYS = {
    "mode",
    "teach_mode",
    "glossary_mode",
    "router",
    "awaiting",
    "awaiting_promo",
    "onboarding_stage",
    "interface_lang",
    "language",
    "level",
    "style",
}


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Жёсткий сброс сессии и перезапуск онбординга.
    Чистим:
      - PTB: context.user_data, context.chat_data
      - наш стор: state.session.user_sessions[chat_id]
    """
    chat_id = update.effective_chat.id

    # 1) PTB-данные
    try:
        (context.user_data or {}).clear()
        (context.chat_data or {}).clear()
    except Exception as e:
        logger.debug("reset: cannot clear PTB data: %r", e)

    # 2) Наш ин-мемори стор
    try:
        sess = user_sessions.get(chat_id)
        if isinstance(sess, dict):
            # точечно вычищаем известные ключи режима
            for k in list(sess.keys()):
                if k in RESET_KEYS:
                    sess.pop(k, None)
        # и на всякий случай — полностью обнулим запись
        user_sessions.pop(chat_id, None)
    except Exception as e:
        logger.debug("reset: cannot clear user_sessions: %r", e)

    # 3) Сообщение пользователю
    try:
        await (update.effective_message or update.message).reply_text("🧹 Сессию очистил. Запускаю онбординг заново.")
    except Exception:
        # тихий фолбэк
        await context.bot.send_message(chat_id, "🧹 Сессию очистил. Запускаю онбординг заново.")

    # 4) Перезапуск онбординга
    # важно: send_onboarding сам выставит корректные поля сессии (например, interface_lang / onboarding_stage)
    await send_onboarding(update, context)
