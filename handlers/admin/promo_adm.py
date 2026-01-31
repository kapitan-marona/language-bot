from __future__ import annotations

import textwrap
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from components.admins import ADMIN_IDS
from components.promo_db import (
    list_codes,
    upsert_code,
    delete_code,
    create_single_use_code,
    normalize_code,
)

# Admin promo panel now works with SQLite table promo_codes (components/promo_db.py)


def _is_admin(update: Update) -> bool:
    u = update.effective_user
    return bool(u and u.id in ADMIN_IDS)


def _kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ Gen ALL_30D (single-use)", callback_data="ADM:PROMO:GEN:ALL30"),
            ],
            [
                InlineKeyboardButton("➕ Gen DUO_30D (single-use)", callback_data="ADM:PROMO:GEN:DUO30"),
            ],
            [InlineKeyboardButton("✍️ Add/Update (manual)", callback_data="ADM:PROMO:ADD")],
            [InlineKeyboardButton("🗑 Delete", callback_data="ADM:PROMO:DEL")],
            [InlineKeyboardButton("🔁 Refresh", callback_data="ADM:PROMO")],
            [
                InlineKeyboardButton("🏠 Home", callback_data="ADM:HOME"),
                InlineKeyboardButton("⬅️ Back", callback_data="ADM:BACK"),
            ],
        ]
    )


def _format_codes(limit: int = 40) -> str:
    codes = list_codes(limit=limit)
    active = sum(1 for c in codes if int(c.get("active") or 0))
    lines = [f"🎟 <b>Promo codes (SQLite)</b>\nActive: {active} / Total: {len(codes)}", ""]
    for c in codes[:limit]:
        days = c.get("days")
        pol = c.get("lang_policy") or "-"
        slots = c.get("lang_slots")
        single = "1x" if int(c.get("is_single_use") or 0) else "∞"
        per_user_once = "per-user-once" if int(c.get("per_user_once") or 0) else ""
        redeemed = f" | used_by:{c.get('redeemed_by')}" if c.get("redeemed_by") else ""
        notes = (c.get("notes") or "").strip()
        if len(notes) > 30:
            notes = notes[:30] + "…"
        lines.append(
            f"• <b>{c.get('code')}</b> — {c.get('kind')} | days:{days or '-'} | policy:{pol} | slots:{slots} | {single} {per_user_once} | {'ON' if int(c.get('active') or 0) else 'off'}{redeemed} {('— ' + notes) if notes else ''}"
        )
    if not codes:
        lines.append("Промокодов нет.")
    lines.append("")
    lines.append("Tip: user uses /promo <code> to redeem.")
    return "\n".join(lines)


async def promo_entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q:
        await q.answer()

    if not _is_admin(update):
        if q:
            await q.edit_message_text("⛔️")
        elif update.message:
            await update.message.reply_text("⛔️")
        return

    text = _format_codes(limit=40)
    if q:
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=_kb())
    elif update.message:
        await update.message.reply_html(text, reply_markup=_kb())


async def promo_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    await q.answer()

    if not _is_admin(update):
        await q.edit_message_text("⛔️")
        return

    data = q.data or ""

    if data == "ADM:PROMO:GEN:ALL30":
        code = create_single_use_code(
            template_kind="ALL_30D",
            days=30,
            lang_policy="all",
            lang_slots=999,
            prefix="ALL30-",
            notes="admin generated single-use ALL_30D",
        )
        msg = (
            f"✅ Generated: <code>{code}</code>\n"
            "Package: ALL (all languages), unlimited messages\n"
            "Duration: 30 days\n"
            "Single-use: yes (one user total)"
        )
        await q.edit_message_text(msg, parse_mode="HTML", reply_markup=_kb())
        return

    if data == "ADM:PROMO:GEN:DUO30":
        code = create_single_use_code(
            template_kind="DUO_30D",
            days=30,
            lang_policy="all",
            lang_slots=2,
            prefix="DUO30-",
            notes="admin generated single-use DUO_30D",
        )
        msg = (
            f"✅ Generated: <code>{code}</code>\n"
            "Package: DUO (2 language slots), unlimited messages\n"
            "Duration: 30 days\n"
            "Single-use: yes (one user total)"
        )
        await q.edit_message_text(msg, parse_mode="HTML", reply_markup=_kb())
        return

    if data == "ADM:PROMO:ADD":
        ctx.user_data["adm_promo_mode"] = "ADD"
        help_text = textwrap.dedent(
            """            ✍️ <b>Add/Update promo (SQLite)</b>

            Send a line in chat:
            <code>CODE;KIND;DAYS_or_0;POLICY(all|english_only);SLOTS;single_use(0/1);per_user_once(0/1);active(0/1);notes</code>

            Example (shareable per-user-once friend 3d):
            <code>friend;FRIEND_3D;3;all;1;0;1;1;shareable each user once</code>

            Example (one-time sale code all 30d):
            <code>SALE1;ALL_30D;30;all;999;1;0;1;single-use</code>
            """
        )
        await q.edit_message_text(help_text, parse_mode="HTML", reply_markup=_kb())
        return

    if data == "ADM:PROMO:DEL":
        ctx.user_data["adm_promo_mode"] = "DEL"
        await q.edit_message_text(
            "🗑 Delete promo: send in chat:\n<code>DEL CODE</code>",
            parse_mode="HTML",
            reply_markup=_kb(),
        )
        return

    await promo_entry(update, ctx)


# Registered in english_bot.py: catches next text message from admin
async def promo_text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    mode = ctx.user_data.get("adm_promo_mode")
    if not mode:
        return  # not our input

    if not (update.effective_user and update.effective_user.id in ADMIN_IDS):
        return

    txt = (update.message.text or "").strip()

    try:
        if mode == "ADD":
            parts = [x.strip() for x in txt.split(";", 8)]
            if len(parts) < 8:
                await update.message.reply_text("⚠️ Не хватает полей. См. формат в панели (Add/Update).")
                return

            code = normalize_code(parts[0])
            kind = parts[1]
            days_raw = parts[2]
            policy = parts[3]
            slots = int(parts[4])
            single_use = int(parts[5])
            per_user_once = int(parts[6])
            active = int(parts[7])
            notes = parts[8] if len(parts) >= 9 else ""

            days = None
            if days_raw and str(days_raw).strip() not in {"0", "-", "none", "null"}:
                days = int(days_raw)

            upsert_code(
                code=code,
                kind=kind,
                days=days,
                lang_policy=policy,
                lang_slots=slots,
                is_single_use=single_use,
                per_user_once=per_user_once,
                active=active,
                notes=notes,
            )
            await update.message.reply_text(f"✅ Saved: {code}")

        elif mode == "DEL":
            parts = txt.split()
            if len(parts) == 2 and parts[0].upper() == "DEL":
                ok = delete_code(parts[1])
                await update.message.reply_text("🗑 Удалён" if ok else "❌ Не найден")
            else:
                await update.message.reply_text("Формат: DEL CODE")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {e}")
    finally:
        ctx.user_data.pop("adm_promo_mode", None)
