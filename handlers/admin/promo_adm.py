# handlers/admin/promo_adm.py
from __future__ import annotations
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from components.admins import ADMIN_IDS
# >>> CHANGED: используем config_store вместо promo_store
from components.config_store import get_kv, set_kv  # >>> ADDED
from datetime import datetime  # >>> ADDED

ALLOWED_TYPES = {"general", "lang_limited", "trial", "discount", "special"}  # >>> ADDED

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

def _list_lines(max_items: int = 50) -> list[str]:  # >>> ADDED
    d = get_kv("__promos__", {}) or {}              # >>> ADDED (кэш списка) — не обязательно
    # если кэша нет — пробегаемся по ключам хранилища (упрощённо, без FS-сканирования)
    # в нашем простом KV — будем хранить список кодов в __promos__
    lines = []                                      # >>> ADDED
    try:
        codes = sorted(d.keys()) if isinstance(d, dict) else []
        for c in codes[:max_items]:
            info = get_kv(f"promo:{c}", {}) or {}
            langs = (info.get("allowed_langs") or "") or "—"
            exp   = (info.get("date") or "") or "—"
            typ   = info.get("type") or "—"
            days  = int(info.get("days") or 0)
            msgs  = int(info.get("messages") or 0)
            limit = int(info.get("limit") or 0)
            used  = int(info.get("used") or 0)
            lines.append(f"• <b>{c}</b> — {typ}; days={days}; msg={msgs}; exp={exp}; limit={limit}; used={used}; langs:{langs}")
    except Exception:
        pass
    return lines

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

    lines = _list_lines()
    text = "🎟 <b>Promo codes</b>\n" + ("\n".join(lines) if lines else "Пока нет сохранённых кодов.")
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
            "<code>CODE;TYPE;DAYS;MESSAGES;DATE;LIMIT;ALLOWED_LANGS</code>\n"
            "TYPE: general|lang_limited|trial|discount|special\n"
            "DATE: YYYY-MM-DD или 0; ALLOWED_LANGS: 0 или CSV (en,de)\n"
            "Пример: <code>best50;trial;0;100;0;50;0</code>",
            parse_mode="HTML",
            reply_markup=_kb()
        )
    elif q.data == "ADM:PROMO:DEL":
        ctx.user_data["adm_promo_mode"] = "DEL"
        await q.edit_message_text("Удаление: отправьте в чат:\n<code>DEL CODE</code>", parse_mode="HTML", reply_markup=_kb())
    else:
        await promo_entry(update, ctx)

def _norm_date(s: str) -> str:  # >>> ADDED
    s = (s or "").strip()
    if not s or s == "0":
        return ""
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except Exception:
        return ""

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
            parts = [x.strip() for x in txt.split(";", 6)]
            if len(parts) < 7:
                await update.message.reply_text(
                    "⚠️ Формат: CODE;TYPE;DAYS;MESSAGES;DATE;LIMIT;ALLOWED_LANGS\n"
                    "Пример: best50;trial;0;100;0;50;0"
                )
                return

            code, typ, days, messages, date_iso, limit, langs = parts
            typ = typ.lower()
            if typ not in ALLOWED_TYPES:
                await update.message.reply_text("⚠️ TYPE должен быть: general|lang_limited|trial|discount|special")
                return

            def _to_int(s): 
                try: return int((s or "0").strip() or 0)
                except: return 0

            days_i = _to_int(days)
            msgs_i = _to_int(messages)
            date_s = _norm_date(date_iso)
            limit_i = _to_int(limit)
            langs_s = (langs or "").strip().lower()
            langs_s = "" if langs_s in {"0", "-"} else langs_s.replace(";", ",").replace(" ", "")

            key = f"promo:{code.lower()}"
            data = get_kv(key, {}) or {}
            data.update({
                "type": typ,
                "days": days_i,
                "messages": msgs_i,
                "date": date_s,           # YYYY-MM-DD или ""
                "limit": limit_i,
                "used": int(data.get("used") or 0),
                "allowed_langs": langs_s, # CSV или ""
            })
            set_kv(key, data)

            # ведём простой список кодов для быстрого вывода
            lst = get_kv("__promos__", {}) or {}
            lst[code.lower()] = True
            set_kv("__promos__", lst)

            await update.message.reply_text("✅ Промокод сохранён.")
        elif mode == "DEL":
            parts = txt.split()
            if len(parts) == 2 and parts[0].upper() == "DEL":
                key = f"promo:{parts[1].lower()}"
                set_kv(key, None)  # мягкое удаление (если get_kv/ set_kv поддерживают None → можешь заменить на явную перезапись {})
                lst = get_kv("__promos__", {}) or {}
                if parts[1].lower() in lst:
                    lst.pop(parts[1].lower(), None)
                    set_kv("__promos__", lst)
                await update.message.reply_text("🗑 Удалён (если существовал).")
            else:
                await update.message.reply_text("Формат: DEL CODE")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {e}")
    finally:
        ctx.user_data.pop("adm_promo_mode", None)
