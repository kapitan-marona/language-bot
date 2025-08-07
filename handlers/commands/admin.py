from config.config import ADMINS
from state.session import user_sessions

async def admin_command(update, context):
    chat_id = update.effective_chat.id
    session = user_sessions.setdefault(chat_id, {})
    if chat_id in ADMINS:
        await update.message.reply_text(
            "👑 Админ-панель:\n"
            "/users — кол-во пользователей\n"
            "/user — стать обычным\n"
            "/reset — сбросить профиль\n"
            "/test — тестовая команда\n"
            "/broadcast — рассылка\n"
            "/promo — промокоды\n"
            "/stats — статистика\n"
            "/session — инфо о сессии\n"
            "/help — список команд"
        )
    else:
        await update.message.reply_text("⛔️")
