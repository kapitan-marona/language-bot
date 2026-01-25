from __future__ import annotations

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from components.admins import ADMIN_IDS
from handlers.commands import admin_cmds


# --- helpers ---
def _is_admin(update: Update) -> bool:
    u = update.effective_user
    return bool(u and u.id in ADMIN_IDS)


def _menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💬 Broadcast", callback_data="ADM:BROAD")],
            [InlineKeyboardButton("🎟 Promo_adm", callback_data="ADM:PROMO")],
            [InlineKeyboardButton("💰 Price", callback_data="ADM:PRICE")],
            [InlineKeyboardButton("👥 Users", callback_data="ADM:USERS")],
            [InlineKeyboardButton("🧪 Test_lang", callback_data="ADM:TESTLANG")],
            [InlineKeyboardButton("📊 Stats", callback_data="ADM:STATS")],
        ]
    )


def _panel_text() -> str:
    return "👑 <b>Admin Panel</b>"


async def _show_home(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q:
        await q.edit_message_text(_panel_text(), parse_mode="HTML", reply_markup=_menu_kb())
    elif update.message:
        await update.message.reply_html(_panel_text(), reply_markup=_menu_kb())


# --- entrypoint (/admin) ---
async def admin_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        await update.message.reply_text("⛔️ Доступ только для администраторов.")
        return
    await update.message.reply_html(_panel_text(), reply_markup=_menu_kb())


# --- callback router for inline admin panel ---
async def admin_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return

    await q.answer()
    data = q.data or ""

    # global navigation
    if data in {"ADM:HOME", "ADM:BACK"}:
        await _show_home(update, ctx)
        return

    if data == "ADM:BROAD":
        await q.edit_message_text(
            "📝 <b>Broadcast</b>\n"
            "Отправь: <code>/broadcast &lt;текст&gt;</code>\n"
            "или сделай reply на сообщение и выполни <code>/broadcast</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Home", callback_data="ADM:HOME")]]
            ),
        )
        return

    if data == "ADM:USERS":
        await admin_cmds.users_command(update, ctx)
        return

    if data == "ADM:STATS":
        await admin_cmds.stats_command(update, ctx)
        return

    if data == "ADM:TESTLANG":
        await q.edit_message_text(
            "🧪 <b>Test language</b>\n"
            "Команда для всех: <code>/test_lang1025 &lt;код&gt;</code>\n"
            "Напр.: <code>/test_lang1025 pt</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Home", callback_data="ADM:HOME")]]
            ),
        )
        return

    # Delegate to submodules (promo / price)
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

    # Fallback: return to home
    await _show_home(update, ctx)
