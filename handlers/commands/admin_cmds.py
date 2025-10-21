from __future__ import annotations
import asyncio, time, os, aiohttp
from telegram import Update
from telegram.ext import ContextTypes

from components.admins import ADMIN_IDS
from components.profile_db import get_all_chat_ids
from components.promo import PROMO_CODES
from state.session import user_sessions

# >>> ADDED: для подсчёта сообщений сегодня из user_usage
from components.usage_db import _connect as usage_connect  # >>> ADDED

# Проверка доступа
def _check_admin(update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    return bool(user_id and user_id in ADMIN_IDS)


# === /adm_help ===
async def adm_help_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _check_admin(update):
        await update.message.reply_text("⛔️")
        return

    text = (
        "👑 <b>Admin commands</b>\n\n"
        "/users — количество активных пользователей\n"
        "/broadcast — рассылка пользователям\n"
        "/stats — статистика использования\n"
        "/test — тестовая команда (проверка uptime)\n"
        "/adm_promo — статистика по промокодам\n"
        "/adm_stars — баланс звёзд бота\n"
        "/adm_help — список админ-команд"
    )

    await update.message.reply_html(text)


# === /adm_promo ===
async def adm_promo_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _check_admin(update):
        await update.message.reply_text("⛔️")
        return

    try:
        total_codes = len(PROMO_CODES)
        types = {}
        for code, info in PROMO_CODES.items():
            t = info.get("type", "unknown")
            types[t] = types.get(t, 0) + 1

        text = ["📊 <b>Промокоды</b>"]
        text.append(f"Всего кодов: {total_codes}")
        for t, n in types.items():
            text.append(f"• {t}: {n}")

        await update.message.reply_html("\n".join(text))
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка при получении статистики: {e}")


# === /broadcast ===
async def broadcast_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _check_admin(update):
        await update.message.reply_text("⛔️")
        return

    text = " ".join(ctx.args).strip() if ctx.args else ""
    if not text and update.message and update.message.reply_to_message:
        text = (update.message.reply_to_message.text or "").strip()
    if not text:
        await update.message.reply_text("📝 Введите текст после команды или сделайте reply на сообщение.")
        return

    try:
        chat_ids = get_all_chat_ids()
    except Exception:
        await update.message.reply_text("⚠️ Не удалось получить список пользователей.")
        return

    sent, failed = 0, 0
    for chat_id in chat_ids:
        try:
            await ctx.bot.send_message(chat_id=chat_id, text=text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await update.message.reply_text(
        f"✅ Рассылка завершена\nОтправлено: {sent}\nОшибок: {failed}\nВсего: {len(chat_ids)}"
    )


# === /test ===
START_TS = time.time()
async def test_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _check_admin(update):
        await update.message.reply_text("⛔️")
        return
    uptime = int(time.time() - START_TS)
    await update.message.reply_text(f"✅ OK\nUptime: {uptime}s")


# === /users ===
async def users_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _check_admin(update):
        await update.message.reply_text("⛔️")
        return
    try:
        chat_ids = get_all_chat_ids()
        await update.message.reply_text(f"👥 Активных пользователей: {len(chat_ids)}")
    except Exception:
        await update.message.reply_text("⚠️ Не удалось получить количество пользователей.")


# === /stats ===
# >>> CHANGED: делаем понятную сводку: Users (DB) / Sessions (RAM) / Messages today
async def stats_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):  # >>> CHANGED
    if not _check_admin(update):                                         # >>> CHANGED
        await update.message.reply_text("⛔️")                            # >>> CHANGED
        return                                                           # >>> CHANGED
                                                                         # >>> CHANGED
    try:                                                                 # >>> CHANGED
        users = len(get_all_chat_ids())                                  # >>> CHANGED
    except Exception:                                                    # >>> CHANGED
        users = 0                                                        # >>> CHANGED
    sessions = len(user_sessions)                                        # >>> CHANGED
                                                                         # >>> CHANGED
    msgs_today = "n/a"                                                   # >>> CHANGED
    try:                                                                 # >>> CHANGED
        con, cur = usage_connect()                                       # >>> CHANGED
        from datetime import datetime, timezone                          # >>> CHANGED
        today = datetime.now(timezone.utc).date().isoformat()            # >>> CHANGED
        cur.execute("SELECT SUM(used_count) FROM user_usage WHERE date_utc=?", (today,))  # >>> CHANGED
        row = cur.fetchone()                                             # >>> CHANGED
        msgs_today = int(row[0]) if row and row[0] is not None else 0    # >>> CHANGED
        con.close()                                                      # >>> CHANGED
    except Exception:                                                    # >>> CHANGED
        pass                                                             # >>> CHANGED
                                                                         # >>> CHANGED
    await update.message.reply_html(                                     # >>> CHANGED
        "📊 <b>Stats</b>\n"                                              # >>> CHANGED
        f"👥 Users (DB): {users}\n"                                      # >>> CHANGED
        f"🧠 Sessions (RAM): {sessions}\n"                                # >>> CHANGED
        f"✉️ Messages today: {msgs_today}"                               # >>> CHANGED
    )                                                                    # >>> CHANGED


# === /adm_stars ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def _format_stars(amount: int, nano: int | None) -> str:
    nano = int(nano or 0)
    if nano <= 0:
        return str(int(amount))
    frac = f"{nano:09d}".rstrip("0")
    return f"{int(amount)}.{frac}"

async def adm_stars_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Показывает реальный баланс звёзд бота через Telegram API."""
    uid = update.effective_user.id if update.effective_user else None
    if not uid or uid not in ADMIN_IDS:
        await update.message.reply_text("❌ Команда доступна только администратору.")
        return

    if not TELEGRAM_TOKEN:
        await update.message.reply_text("⚠️ TELEGRAM_TOKEN не задан в окружении.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMyStarBalance"

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url) as resp:
                data = await resp.json()

        if not data.get("ok"):
            desc = data.get("description") or "unknown error"
            await update.message.reply_text(f"⚠️ Ошибка при запросе баланса: {desc}")
            return

        res = data.get("result") or {}
        amount = int(res.get("amount", 0))
        nano = int(res.get("nanostar_amount", 0))

        stars_text = _format_stars(amount, nano)
        stars_float = amount + (nano / 1_000_000_000)
        euros = stars_float * 0.01  # 1 Star ≈ €0.01

        await update.message.reply_text(
            f"⭐ Баланс бота: {stars_text} Stars\n"
            f"💶 В евро: ~ {euros:.2f} €"
        )

    except Exception as e:
        await update.message.reply_text(f"⚠️ Не удалось получить баланс: {e}")
