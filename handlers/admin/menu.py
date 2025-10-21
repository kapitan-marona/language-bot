from __future__ import annotations
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from components.admins import ADMIN_IDS
from handlers.commands import admin_cmds

# Простой чек прав
def _is_admin(update: Update) -> bool:
    u = update.effective_user
    return bool(u and u.id in ADMIN_IDS)

def _menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Broadcast", callback_data="ADM:BROAD")],
        [InlineKeyboardButton("🎟 Promo_adm", callback_data="ADM:PROMO")],
        [InlineKeyboardButton("💰 Price", callback_data="ADM:PRICE")],
        [InlineKeyboardButton("👥 Users", callback_data="ADM:USERS")],
        [InlineKeyboardButton("🧪 Test_lang", callback_data="ADM:TESTLANG")],
        [InlineKeyboardButton("📊 Stats", callback_data="ADM:STATS")],
    ])

async def admin_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        await update.message.reply_text("⛔️ Доступ только для администраторов.")
        return
    await update.message.reply_text("👑 Admin Panel", reply_markup=_menu_kb())

async def admin_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "ADM:BROAD":
        await q.edit_message_text("📝 Отправь /broadcast <текст> или сделай reply на сообщение и выполни /broadcast")
        return

    if data == "ADM:USERS":
        await admin_cmds.users_command(update, ctx)
        return

    if data == "ADM:STATS":
        await admin_cmds.stats_command(update, ctx)
        return

    if data == "ADM:TESTLANG":
        await q.edit_message_text("Команда для всех: /test_lang1025 <код>\nНапр.: /test_lang1025 pt")
        return

    # Делегируем в под-модули промо и цен
    if data.startswith("ADM:PROMO"):
        from handlers.admin.promo_adm import promo_entry, promo_router
        if data == "ADM:PROMO":
            await promo_entry(update, ctx)
        else:
            await promo_router(update, ctx)
        return

    if data.startswith("ADM:PRICE"):
        from handlers.admin.price_adm import price_entry, price_router
        if data == "ADM:PRICE":
            await price_entry(update, ctx)
        else:
            await price_router(update, ctx)
        return
