from __future__ import annotations
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from components.admins import ADMIN_IDS
from components.promo_store import list_codes, upsert_code, delete_code

def _is_admin(update: Update) -> bool:
    u = update.effective_user
    return bool(u and u.id in ADMIN_IDS)

def _kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add/Update", callback_data="ADM:PROMO:ADD")],
        [InlineKeyboardButton("🗑 Delete", callback_data="ADM:PROMO:DEL")],
        [InlineKeyboardButton("🔁 Refresh", callback_data="ADM:PROMO")],
        [InlineKeyboardButton("⬅️ Back", callback_data="ADM:BACK")],
    ])

async def promo_entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q:
        await q.answer()
    if not _is_admin(update):
        if q:
            await q.edit_message_text("⛔️")
        else:
            await update.message.reply_text("⛔️")
        return

    codes = list_codes()
    active = sum(1 for c in codes if c.get("active"))
    lines = [f"🎟 <b>Promo codes</b>\nActive: {active} / Total: {len(codes)}", ""]
    for c in codes[:50]:
        exp = c.get("expires_at") or "-"
        langs = ",".join(c.get("langs", [])) or "-"
        lines.append(f"• <b>{c['code']}</b> — {c.get('type')}/{c.get('value')} | langs:{langs} | exp:{exp} | {'ON' if c.get('active') else 'off'}")
    text = "\n".join(lines) if codes else "Промокодов нет."

    if q:
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=_kb())
    else:
        await update.message.reply_html(text, reply_markup=_kb())

async def promo_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "ADM:PROMO:ADD":
        ctx.user_data["adm_promo_mode"] = "ADD"
        await q.edit_message_text(
            "Введите строку:\n"
            "<code>CODE;TYPE;VALUE;EXPIRES_EPOCH_or_0;langs_csv</code>\n"
            "Пример: <code>BF25;percent;25;0;en,de,fr</code>\n"
            "TYPE: percent|fixed|days|messages",
            parse_mode="HTML",
            reply_markup=_kb()
        )
    elif q.data == "ADM:PROMO:DEL":
        ctx.user_data["adm_promo_mode"] = "DEL"
        await q.edit_message_text("Удаление: отправьте в чат:\n<code>DEL CODE</code>", parse_mode="HTML", reply_markup=_kb())
    else:
        await promo_entry(update, ctx)

# Ловим следующую текстовую реплику от админа (зарегистрировано в english_bot.py)
async def promo_text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    mode = ctx.user_data.get("adm_promo_mode")
    if not mode:
        return  # не наш ввод — пропускаем дальше
    if not (update.effective_user and update.effective_user.id in ADMIN_IDS):
        return

    txt = (update.message.text or "").strip()
    try:
        if mode == "ADD":
            code, typ, val, exp, langs = [x.strip() for x in txt.split(";", 4)]
            value = int(val)
            expires = int(exp) or None
            langs_list = [s.strip() for s in langs.split(",") if s.strip()]
            if typ not in {"percent", "fixed", "days", "messages"}:
                await update.message.reply_text("⚠️ TYPE должен быть: percent|fixed|days|messages")
            else:
                upsert_code(code, typ, value, expires, langs_list, active=True)
                await update.message.reply_text(f"✅ Промокод {code} сохранён/обновлён")
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
