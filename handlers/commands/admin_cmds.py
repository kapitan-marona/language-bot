from __future__ import annotations

import asyncio
import os
import time
import aiohttp

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.error import RetryAfter, Forbidden, BadRequest, TimedOut, NetworkError

from components.admins import ADMIN_IDS
from components.profile_db import (
    get_all_chat_ids,
    delete_user,
    get_chat_ids_by_interface_lang,
    get_chat_ids_active_last_days,
    get_chat_ids_active_last_days_by_interface_lang,
)
from components.promo import PROMO_CODES
from state.session import user_sessions

# для подсчёта сообщений сегодня из user_usage
from components.usage_db import _connect as usage_connect


# Проверка доступа
def _check_admin(update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    return bool(user_id and user_id in ADMIN_IDS)


def _nav_kb() -> InlineKeyboardMarkup:
    # Единая навигация для экранной админки
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data="ADM:HOME")]])


async def _out(
    update: Update,
    text: str,
    *,
    parse_mode: str | None = None,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Пишем в чат или редактируем экран админки, если пришли из callback."""
    q = update.callback_query
    if q:
        await q.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
        return

    if update.message:
        if parse_mode == "HTML":
            await update.message.reply_html(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)


def _audience_label(flt: dict | None) -> str:
    if not flt:
        return "All users"
    mode = flt.get("mode")
    if mode == "ALL":
        return "All users"
    if mode == "LANG":
        return f"UI lang: {flt.get('lang')}"
    if mode == "ACTIVE":
        return f"Active last {flt.get('days', 7)} days"
    if mode == "ACTIVE_LANG":
        return f"Active last {flt.get('days', 7)} days + {flt.get('lang')}"
    return "All users"


def _resolve_audience(flt: dict | None) -> list[int]:
    """Возвращает список chat_id по выбранному фильтру админки."""
    if not flt:
        return get_all_chat_ids()

    mode = flt.get("mode")
    if mode == "ALL":
        return get_all_chat_ids()

    if mode == "LANG":
        lang = str(flt.get("lang") or "").strip()
        return get_chat_ids_by_interface_lang(lang) if lang else get_all_chat_ids()

    if mode == "ACTIVE":
        days = int(flt.get("days") or 7)
        return get_chat_ids_active_last_days(days)

    if mode == "ACTIVE_LANG":
        days = int(flt.get("days") or 7)
        lang = str(flt.get("lang") or "").strip()
        return (
            get_chat_ids_active_last_days_by_interface_lang(days=days, interface_lang=lang)
            if lang
            else get_chat_ids_active_last_days(days)
        )

    return get_all_chat_ids()


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
        for _, info in PROMO_CODES.items():
            t = info.get("type", "unknown")
            types[t] = types.get(t, 0) + 1

        lines = ["📊 <b>Промокоды</b>", f"Всего кодов: {total_codes}"]
        for t, n in types.items():
            lines.append(f"• {t}: {n}")

        await update.message.reply_html("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка при получении статистики: {e}")


# === /broadcast ===
async def broadcast_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Тихая рассылка:
    - всегда disable_notification=True
    - троттлинг + обработка RetryAfter
    - авто-чистка базы, если пользователь заблокировал/недоступен
    - прогресс админу
    - защита от параллельных рассылок

    Audience:
    - если в админке выбран фильтр (ctx.user_data['adm_broadcast_filter']),
      рассылаем только по нему.
    """
    if not _check_admin(update):
        if update.message:
            await update.message.reply_text("⛔️")
        return

    if not update.message:
        return

    # ---- lock: не даём запустить 2 рассылки одновременно
    if ctx.application.bot_data.get("broadcast_running"):
        await update.message.reply_text("⏳ Рассылка уже идёт. Дождись завершения.")
        return
    ctx.application.bot_data["broadcast_running"] = True

    # выбранная аудитория из админки (если есть)
    flt = ctx.user_data.get("adm_broadcast_filter")

    try:
        text = " ".join(ctx.args).strip() if ctx.args else ""
        if not text and update.message.reply_to_message:
            text = (update.message.reply_to_message.text or "").strip()

        if not text:
            await update.message.reply_text(
                "📝 Введите текст после команды или сделайте reply на текстовое сообщение."
            )
            return

        try:
            chat_ids = _resolve_audience(flt)
        except Exception:
            await update.message.reply_text("⚠️ Не удалось получить список пользователей по выбранной аудитории.")
            return

        total = len(chat_ids)
        if total == 0:
            await update.message.reply_text("По выбранной аудитории пользователей не найдено.")
            return

        audience_title = _audience_label(flt)
        progress_msg = await update.message.reply_text(
            f"📣 Тихая рассылка началась\n"
            f"Аудитория: {audience_title}\n"
            f"Получателей: {total}\n"
            f"Отправлено: 0\nОшибок: 0\nУдалено из базы: 0"
        )

        sent = 0
        failed = 0
        deleted = 0

        last_edit_ts = time.time()
        EDIT_EVERY_SEC = 2.5
        THROTTLE_SEC = 0.05

        async def update_progress(force: bool = False) -> None:
            nonlocal last_edit_ts
            now = time.time()
            if (not force) and (now - last_edit_ts < EDIT_EVERY_SEC):
                return
            last_edit_ts = now
            try:
                await progress_msg.edit_text(
                    f"📣 Тихая рассылка идёт…\n"
                    f"Аудитория: {audience_title}\n"
                    f"Получателей: {total}\n"
                    f"Отправлено: {sent}\n"
                    f"Ошибок: {failed}\n"
                    f"Удалено из базы: {deleted}"
                )
            except Exception:
                pass

        def should_delete_on_bad_request(err_text: str) -> bool:
            t = (err_text or "").lower()
            return (
                "chat not found" in t
                or "user is deactivated" in t
                or "bot was blocked" in t
                or "bot can't initiate conversation" in t
            )

        for chat_id in chat_ids:
            try:
                await ctx.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    disable_notification=True,
                )
                sent += 1

            except RetryAfter as e:
                wait_s = float(getattr(e, "retry_after", 1.0)) + 0.5
                await asyncio.sleep(wait_s)
                try:
                    await ctx.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        disable_notification=True,
                    )
                    sent += 1
                except (Forbidden, BadRequest) as e2:
                    failed += 1
                    err_text = str(e2)
                    if isinstance(e2, Forbidden) or should_delete_on_bad_request(err_text):
                        try:
                            delete_user(chat_id)
                            deleted += 1
                        except Exception:
                            pass
                except Exception:
                    failed += 1

            except Forbidden:
                failed += 1
                try:
                    delete_user(chat_id)
                    deleted += 1
                except Exception:
                    pass

            except BadRequest as e:
                failed += 1
                if should_delete_on_bad_request(str(e)):
                    try:
                        delete_user(chat_id)
                        deleted += 1
                    except Exception:
                        pass

            except (TimedOut, NetworkError):
                failed += 1

            except Exception:
                failed += 1

            await update_progress(force=False)
            await asyncio.sleep(THROTTLE_SEC)

        await update_progress(force=True)

        final_text = (
            f"✅ Тихая рассылка завершена\n"
            f"Аудитория: {audience_title}\n"
            f"Получателей: {total}\n"
            f"Отправлено: {sent}\n"
            f"Ошибок: {failed}\n"
            f"Удалено из базы: {deleted}"
        )
        try:
            await progress_msg.edit_text(final_text)
        except Exception:
            await update.message.reply_text(final_text)

    finally:
        ctx.application.bot_data["broadcast_running"] = False
        # сбрасываем фильтр после попытки рассылки, чтобы не применять случайно повторно
        if "adm_broadcast_filter" in ctx.user_data:
            ctx.user_data.pop("adm_broadcast_filter", None)


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
        await _out(update, "⛔️")
        return
    try:
        chat_ids = get_all_chat_ids()
        await _out(
            update,
            f"👥 <b>Users</b>\nАктивных пользователей: <b>{len(chat_ids)}</b>",
            parse_mode="HTML",
            reply_markup=_nav_kb() if update.callback_query else None,
        )
    except Exception:
        await _out(
            update,
            "⚠️ Не удалось получить количество пользователей.",
            reply_markup=_nav_kb() if update.callback_query else None,
        )


# === /stats ===
async def stats_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _check_admin(update):
        await _out(update, "⛔️")
        return

    try:
        users = len(get_all_chat_ids())
    except Exception:
        users = 0
    sessions = len(user_sessions)

    msgs_today = "n/a"
    try:
        con, cur = usage_connect()
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).date().isoformat()
        cur.execute("SELECT SUM(used_count) FROM user_usage WHERE date_utc=?", (today,))
        row = cur.fetchone()
        msgs_today = int(row[0]) if row and row[0] is not None else 0
        con.close()
    except Exception:
        pass

    text = (
        "📊 <b>Stats</b>\n"
        f"👥 Users (DB): <b>{users}</b>\n"
        f"🧠 Sessions (RAM): <b>{sessions}</b>\n"
        f"✉️ Messages today: <b>{msgs_today}</b>"
    )
    await _out(
        update,
        text,
        parse_mode="HTML",
        reply_markup=_nav_kb() if update.callback_query else None,
    )


# === /adm_stars ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


async def adm_stars_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Показывает реальный баланс звёзд бота через Telegram API."""
    uid = update.effective_user.id if update.effective_user else None
    if not uid or uid not in ADMIN_IDS:
        await _out(update, "❌ Команда доступна только администратору.")
        return

    if not TELEGRAM_TOKEN:
        await _out(update, "⚠️ TELEGRAM_TOKEN не задан в окружении.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMyStarBalance"

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url) as resp:
                data = await resp.json()

        if not data.get("ok"):
            desc = data.get("description") or "unknown error"
            await _out(update, f"⚠️ Ошибка Telegram API: {desc}", reply_markup=_nav_kb() if update.callback_query else None)
            return

        result = data.get("result") or {}
        amount = int(result.get("amount", 0))
        nano = int(result.get("nanostar_amount", 0))

        stars_float = amount + (nano / 1_000_000_000)
        euros = stars_float * 0.01  # 1 Star ≈ €0.01

        if nano:
            frac = f"{nano:09d}".rstrip("0")
            stars_text = f"{amount}.{frac}"
        else:
            stars_text = str(amount)

        text = (
            "⭐ <b>Stars balance</b>\n"
            f"⭐ Баланс бота: <b>{stars_text}</b> Stars\n"
            f"💶 В евро: ~ <b>{euros:.2f}</b> €"
        )
        await _out(update, text, parse_mode="HTML", reply_markup=_nav_kb() if update.callback_query else None)

    except Exception as e:
        await _out(update, f"⚠️ Не удалось получить баланс: {e}", reply_markup=_nav_kb() if update.callback_query else None)
