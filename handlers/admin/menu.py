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


def _broadcast_audience_label(flt: dict | None) -> str:
    if not flt:
        return "👥 All users"
    mode = flt.get("mode")
    if mode == "ALL":
        return "👥 All users"
    if mode == "LANG":
        return f"🌍 UI lang: {flt.get('lang')}"
    if mode == "ACTIVE":
        return f"🔥 Active last {flt.get('days', 7)} days"
    if mode == "ACTIVE_LANG":
        return f"🔥 Active last {flt.get('days', 7)} days + 🌍 {flt.get('lang')}"
    return "👥 All users"


def _broadcast_kb(selected: dict | None) -> InlineKeyboardMarkup:
    # RU/EN correspond to interface_lang codes stored in DB: 'ru' / 'en'
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("👥 All users", callback_data="ADM:BROAD:SET:ALL")],
            [InlineKeyboardButton("🔥 Active 7 days", callback_data="ADM:BROAD:SET:ACTIVE7")],
            [
                InlineKeyboardButton("🌍 RU (all)", callback_data="ADM:BROAD:SET:LANG:ru"),
                InlineKeyboardButton("🌍 EN (all)", callback_data="ADM:BROAD:SET:LANG:en"),
            ],
            [
                InlineKeyboardButton("🔥7d + RU", callback_data="ADM:BROAD:SET:ACTIVE7_LANG:ru"),
                InlineKeyboardButton("🔥7d + EN", callback_data="ADM:BROAD:SET:ACTIVE7_LANG:en"),
            ],
            [
                InlineKeyboardButton("🏠 Home", callback_data="ADM:HOME"),
                InlineKeyboardButton("⬅️ Back", callback_data="ADM:BACK"),
            ],
        ]
    )


def _broadcast_text(selected: dict | None) -> str:
    aud = _broadcast_audience_label(selected)
    return (
        "💬 <b>Broadcast</b>\n"
        f"Audience: <b>{aud}</b>\n\n"
        "1) Выбери аудиторию кнопками ниже\n"
        "2) Запусти рассылку командой:\n"
        "<code>/broadcast текст</code>\n\n"
        "Рассылка всегда <b>тихая</b> (без звука), с авто-чисткой недоступных пользователей."
    )


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

    # Broadcast screen + audience selection
    if data == "ADM:BROAD":
        selected = ctx.user_data.get("adm_broadcast_filter")
        await q.edit_message_text(
            _broadcast_text(selected),
            parse_mode="HTML",
            reply_markup=_broadcast_kb(selected),
        )
        return

    if data.startswith("ADM:BROAD:SET:"):
        # store selection in user_data; broadcast_command will read it
        tail = data.split("ADM:BROAD:SET:", 1)[1]

        flt: dict
        if tail == "ALL":
            flt = {"mode": "ALL"}
        elif tail == "ACTIVE7":
            flt = {"mode": "ACTIVE", "days": 7}
        elif tail.startswith("LANG:"):
            lang = tail.split(":", 1)[1]
            flt = {"mode": "LANG", "lang": lang}
        elif tail.startswith("ACTIVE7_LANG:"):
            lang = tail.split(":", 1)[1]
            flt = {"mode": "ACTIVE_LANG", "days": 7, "lang": lang}
        else:
            flt = {"mode": "ALL"}

        ctx.user_data["adm_broadcast_filter"] = flt
        await q.edit_message_text(
            _broadcast_text(flt),
            parse_mode="HTML",
            reply_markup=_broadcast_kb(flt),
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
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data="ADM:HOME")]]),
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
