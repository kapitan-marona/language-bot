# handlers/commands/promo.py
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timezone, date

from components.i18n import get_ui_lang
from components.profile_db import set_user_promo, save_user_profile, get_user_profile
from components.promo_store import get_promo_info
from components.config_store import get_kv, set_kv

import logging
logger = logging.getLogger(__name__)

def _today_str() -> str:
    return date.today().isoformat()

async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /promo              → показать статус текущего промо
    /promo <code>       → активировать промо
    """
    chat_id = update.effective_chat.id
    ui = get_ui_lang(update, context)
    args = context.args or []

    profile = get_user_profile(chat_id) or {"chat_id": chat_id}

    # Без аргументов — показать краткий статус
    if not args:
        code = (profile.get("promo_code_used") or "").strip().lower()
        if not code:
            txt = "Промокод не активирован." if ui == "ru" else "No promo code is active."
            await update.message.reply_text(txt)
            return
        bits = [f"🎟 {('Промокод' if ui=='ru' else 'Promo code')} {code}"]
        if profile.get("promo_days"):
            bits.append(("📅 дней: " if ui=="ru" else "📅 days: ") + str(int(profile["promo_days"])))
        if profile.get("promo_hard_expire"):
            bits.append(("⏱ до: " if ui=="ru" else "⏱ until: ") + profile["promo_hard_expire"])
        if profile.get("promo_messages_quota"):
            used = int(profile.get("promo_messages_used") or 0)
            quota = int(profile.get("promo_messages_quota") or 0)
            bits.append(("✉️ сообщения: " if ui=="ru" else "✉️ messages: ") + f"{used}/{quota}")
        if profile.get("promo_allowed_langs"):
            bits.append(("🌍 языки: " if ui=="ru" else "🌍 langs: ") + profile["promo_allowed_langs"].upper())
        await update.message.reply_text("\n".join(bits))
        return

    # Активация
    code = args[0].strip().lower()
    info = get_promo_info(code)
    if not info:
        await update.message.reply_text("❌ Промокод не найден или недействителен." if ui=="ru" else "❌ Promo code not found or invalid.")
        return

    # лимит активаций
    used = int(info.get("used") or 0)
    limit = int(info.get("limit") or 0)
    if limit and used >= limit:
        await update.message.reply_text("⚠️ Лимит активаций промокода исчерпан." if ui=="ru" else "⚠️ Promo activation limit reached.")
        return

    # срок по дате (если указан)
    d = (info.get("date") or "").strip()
    if d and _today_str() > d:
        await update.message.reply_text("⚠️ Срок действия промокода истёк." if ui=="ru" else "⚠️ Promo code has expired.")
        return

    ptype    = (info.get("type") or "").strip().lower()
    days     = int(info.get("days") or 0)
    messages = int(info.get("messages") or 0)
    allowed  = (info.get("allowed_langs") or "").strip().lower()
    hard_exp = d  # YYYY-MM-DD или ""

    now_iso = datetime.now(timezone.utc).isoformat()

    set_user_promo(
        chat_id=chat_id,
        code=code,
        promo_type=ptype,
        activated_at=now_iso,
        days=days or None,
        allowed_langs_csv=allowed or None,   # >>> ADDED
        messages_quota=messages or None,     # >>> ADDED
        hard_expire=hard_exp or None,        # >>> ADDED
    )
    # сброс персонального счётчика
    save_user_profile(chat_id, promo_messages_used=0)

    # увеличим глобальный used в карточке промо
    info["used"] = used + 1
    set_kv(f"promo:{code}", info)

    # ответ пользователю
    bits = ["✅ " + ("Промокод активирован!" if ui=="ru" else "Promo code activated!")]
    if days > 0: bits.append(("📅 действует " if ui=="ru" else "📅 valid for ") + f"{days} " + ("дн." if ui=="ru" else "days"))
    if messages > 0: bits.append(("✉️ квота сообщений: " if ui=="ru" else "✉️ messages quota: ") + str(messages))
    if hard_exp: bits.append(("⏱ до: " if ui=="ru" else "⏱ until: ") + hard_exp)
    if allowed: bits.append(("🌍 языки: " if ui=="ru" else "🌍 langs: ") + allowed.upper().replace(",", ", "))
    await update.message.reply_text("\n".join(bits))
