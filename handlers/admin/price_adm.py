from __future__ import annotations

import sqlite3
import time

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from components.admins import ADMIN_IDS
from components.config_store import set_kv, get_kv  # KV-хранилище цен (JSON)
from components.profile_db import DB_PATH as PROFILES_DB_PATH


def _is_admin(update: Update) -> bool:
    u = update.effective_user
    return bool(u and u.id in ADMIN_IDS)


def _kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⭐ Balance (Stars)", callback_data="ADM:PRICE:STARS")],
            [InlineKeyboardButton("🧾 Subs count", callback_data="ADM:PRICE:SUBS")],
            [InlineKeyboardButton("💶 Change price (Stars)", callback_data="ADM:PRICE:SET_STARS")],
            [InlineKeyboardButton("₽ Change price (RUB)", callback_data="ADM:PRICE:SET_RUB")],
            [
                InlineKeyboardButton("🏠 Home", callback_data="ADM:HOME"),
                InlineKeyboardButton("⬅️ Back", callback_data="ADM:BACK"),
            ],
        ]
    )


async def price_entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q:
        await q.answer()

    if not _is_admin(update):
        if q:
            await q.edit_message_text("⛔️")
        elif update.message:
            await update.message.reply_text("⛔️")
        return

    text = "💰 <b>Price / Billing</b>"
    if q:
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=_kb())
    elif update.message:
        await update.message.reply_html(text, reply_markup=_kb())


async def price_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    await q.answer()
    data = q.data or ""

    if not _is_admin(update):
        await q.edit_message_text("⛔️")
        return

    if data == "ADM:PRICE:STARS":
        # переиспользуем готовую команду (выводит баланс звёзд/€)
        from handlers.commands.admin_cmds import adm_stars_command

        await adm_stars_command(update, ctx)
        return

    if data == "ADM:PRICE:SUBS":
        # считаем активные подписки по полю premium_until в user_profiles
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        conn = sqlite3.connect(PROFILES_DB_PATH)
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT COUNT(*) FROM user_profiles WHERE premium_until IS NOT NULL AND premium_until >= ?",
                (now_iso,),
            )
            n = cur.fetchone()[0] or 0
        except Exception:
            n = "n/a"
        finally:
            conn.close()
        await q.edit_message_text(f"🧾 <b>Subs</b>\nАктивных подписок: {n}", parse_mode="HTML", reply_markup=_kb())
        return

    if data == "ADM:PRICE:SET_STARS":
        ctx.user_data["adm_price_mode"] = "SET_STARS"
        current = get_kv("PRICE_STARS") or "—"
        await q.edit_message_text(
            f"💶 <b>Change price (Stars)</b>\nТекущая цена: <b>{current}</b>\n\n"
            "Отправь новую в чат, напр.: <code>PRICE_STARS 499</code>",
            parse_mode="HTML",
            reply_markup=_kb(),
        )
        return

    if data == "ADM:PRICE:SET_RUB":
        ctx.user_data["adm_price_mode"] = "SET_RUB"
        current = get_kv("PRICE_RUB") or "—"
        await q.edit_message_text(
            f"₽ <b>Change price (RUB)</b>\nТекущая цена: <b>{current}</b>\n\n"
            "Отправь новую в чат, напр.: <code>PRICE_RUB 399</code>",
            parse_mode="HTML",
            reply_markup=_kb(),
        )
        return

    # refresh / fallback
    await price_entry(update, ctx)


# Ловим следующую текстовую реплику от админа (зарегистрировано в english_bot.py)
async def price_text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    mode = ctx.user_data.get("adm_price_mode")
    if not mode:
        return
    if not (update.effective_user and update.effective_user.id in ADMIN_IDS):
        return

    txt = (update.message.text or "").strip()
    try:
        key, val = txt.split()
        val_int = int(val)

        if mode == "SET_STARS" and key.upper() == "PRICE_STARS":
            set_kv("PRICE_STARS", val_int)
            await update.message.reply_text(f"✅ PRICE_STARS = {val_int}")
        elif mode == "SET_RUB" and key.upper() == "PRICE_RUB":
            set_kv("PRICE_RUB", val_int)
            await update.message.reply_text(f"✅ PRICE_RUB = {val_int}")
        else:
            await update.message.reply_text("⚠️ Формат: PRICE_STARS 499 или PRICE_RUB 399")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {e}")
    finally:
        ctx.user_data.pop("adm_price_mode", None)
