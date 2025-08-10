from telegram import Update
from telegram.ext import ContextTypes
from components.profile_db import get_user_profile, save_user_profile
from components.promo import check_promo_code, activate_promo, is_promo_valid

async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args or []
    code = (args[0] if args else "").strip()

    profile = get_user_profile(chat_id) or {"chat_id": chat_id}

    if not code:
        # Show status
        if profile.get("promo_type") and is_promo_valid(profile):
            await update.message.reply_text(f"🎟️ Активно: {profile['promo_type']} — осталось {profile.get('promo_days', '?')} дн.")
        else:
            await update.message.reply_text("🎟️ Промокод не активирован. Отправь: /promo <код>")
        return

    data = check_promo_code(code)
    if not data:
        await update.message.reply_text("❌ Неизвестный промокод.")
        return

    ok, msg = activate_promo(profile, code)
    if ok:
        save_user_profile(
            chat_id,
            promo_code_used=profile.get("promo_code_used"),
            promo_type=profile.get("promo_type"),
            promo_activated_at=profile.get("promo_activated_at"),
            promo_days=profile.get("promo_days"),
        )
    await update.message.reply_text(msg)
