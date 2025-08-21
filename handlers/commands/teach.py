# handlers/commands/teach.py
from __future__ import annotations
import re
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,   # ← добавили
    MessageHandler,
    filters,
)
from components.training_db import set_consent, has_consent, add_glossary, get_glossary

__all__ = [
    "build_teach_handler",
    "teach_start",
    "glossary_cmd",
    "consent_on",
    "consent_off",
]

ASK_SRC_DST = 1
ASK_LIST    = 2
ASK_CORR    = 3  # fallback для одиночной пары (совместимость)

_SEP_VARIANTS = [" — ", " - ", " -> ", " → ", "—", "-", "->", "→"]

_LANG_PAIR_RE = re.compile(
    r"^\s*([A-Za-z]{2})\s*(?:-|—|->|→|\s)\s*([A-Za-z]{2})\s*$"
)

_BAD_RU = [
    r"\bхуй\b", r"\bхуе", r"\bпизд", r"\bбляд", r"\bебат", r"\bебан", r"\bсука\b",
    r"\bсуки\b", r"\bмраз", r"\bублюд", r"\bговн", r"\bдерьм"
]
_BAD_EN = [
    r"\bfuck", r"\bshit\b", r"\basshole\b", r"\bbitch\b", r"\bdick\b", r"\bcunt\b",
    r"\bslut\b", r"\bwhore\b"
]
_BAD_RE = re.compile("(" + "|".join(_BAD_RU + _BAD_EN) + ")", re.IGNORECASE)


def _split_pair(text: str):
    for sep in _SEP_VARIANTS:
        if sep in text:
            a, b = text.split(sep, 1)
            return a.strip(), b.strip()
    m = re.match(r'^\s*"?(.+?)"?\s*[-—→>]+\s*"?(.+?)"?\s*$', text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, None


def _contains_bad_words(s: str) -> bool:
    return bool(_BAD_RE.search(s or ""))


def _parse_lang_pair(s: str):
    m = _LANG_PAIR_RE.match((s or ""))
    if not m:
        return None, None
    return m.group(1).lower(), m.group(2).lower()


# --------- СОГЛАСИЕ НА РЕЖИМ TEACH ----------
async def consent_on(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    set_consent(update.effective_user.id, True)
    await update.effective_message.reply_text(
        "✅ Режим корректировок включён.\n\n"
        "Как пользоваться:\n"
        "1) Отправь языковую пару двумя буквами: en-ru, ru-en, en-fi… Если сомневаешься — /codes.\n"
        "2) Затем списком пришли строки «фраза — перевод», по одной на строке.\n\n"
        "Важно: это два разных сообщения — сначала пара языков, жди подтверждения, потом список пар.\n\n"
        "Пример:\n"
        "I feel you — Понимаю тебя\n"
        "Break a leg — Удачи!\n\n"
        "Готово — я сохраню всё в /glossary.\n"
        "Спасибо! Ты делаешь Мэтта лучше ❤️"
    )


async def consent_off(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    set_consent(update.effective_user.id, False)
    await update.effective_message.reply_text(
        "Окей, режим корректировок выключен. Вернёшься — скажи /consent_on 🙂"
    )


# --------- ВХОД В РЕЖИМ TEACH ----------
async def teach_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not has_consent(update.effective_user.id):
        await update.effective_message.reply_text("Сначала включи согласие: /consent_on 🙂")
        return ConversationHandler.END

    # Если пришли по inline-кнопке — аккуратно ответим на callback, чтобы не висел "часик".
    q = getattr(update, "callback_query", None)
    if q:
        try:
            await q.answer()
        except Exception:
            pass

    await update.effective_message.reply_text(
        "Отправь языковую пару (например, en-ru или ru-en). Я на связи 😉"
    )
    return ASK_SRC_DST


async def teach_src_dst(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = (update.message.text or "").strip()
    src, dst = _parse_lang_pair(t)
    if not src or not dst:
        await update.effective_message.reply_text(
            "Нужно указать пару двухбуквенных кодов: en-ru, en-fi, ru-en, ru-es и т.д. Попробуешь ещё раз? 🙂\n"
            "Подсказка по кодам — /codes"
        )
        return ASK_SRC_DST

    ctx.user_data["teach_src"], ctx.user_data["teach_dst"] = src, dst
    await update.effective_message.reply_text(
        "Принято! Теперь пришли список строк «фраза — перевод» (по одной на строке).\n"
        "Например:\n"
        "I feel you — Понимаю тебя\n"
        "Break a leg — Удачи!"
    )
    return ASK_LIST


def _parse_pairs_block(block: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for raw_line in (block or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        p, c = _split_pair(line)
        if p and c:
            pairs.append((p, c))
    return pairs


async def teach_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    src = ctx.user_data.get("teach_src", "en")
    dst = ctx.user_data.get("teach_dst", "ru")
    block = (update.message.text or "").strip()

    pairs = _parse_pairs_block(block)

    if not pairs:
        ctx.user_data["teach_phrase"] = block
        await update.effective_message.reply_text(
            "Нужен формат «фраза — перевод», по одной паре на строке. Попробуем ещё раз? 🙂"
        )
        return ASK_CORR

    saved = []
    skipped_bad = 0
    for phrase, corr in pairs:
        if _contains_bad_words(phrase) or _contains_bad_words(corr):
            skipped_bad += 1
            continue
        add_glossary(update.effective_user.id, src, dst, phrase, corr)
        saved.append(f"{phrase} — {corr}")

    if not saved and skipped_bad > 0:
        await update.effective_message.reply_text(
            "❌ Не сохранил: найден ненормативный контент. Давай без этого, ок? 😉"
        )
        return ConversationHandler.END

    if saved:
        header = "✅ Всё получилось, спасибо!\nВ глоссарий добавлено:\n"
        body = "\n".join(saved[:50])
        footer = "\n\nЕщё примеры — снова /teach. Посмотреть — /glossary."
        if skipped_bad:
            footer += f"\n(Пропущено из-за ненормативной лексики: {skipped_bad})"
        await update.effective_message.reply_text(header + body + footer)
    else:
        await update.effective_message.reply_text(
            "Я не увидел пар «фраза — перевод». Пришли их по одной на строке.\n"
            "Например: I feel you — Понимаю тебя 🙂"
        )

    return ConversationHandler.END


async def teach_correction(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Fallback: одиночная пара (сценарий совместимости)
    src = ctx.user_data.get("teach_src", "en")
    dst = ctx.user_data.get("teach_dst", "ru")
    phrase = ctx.user_data.get("teach_phrase")
    corr = (update.message.text or "").strip()
    if not phrase:
        p, c = _split_pair(corr)
        if p and c:
            phrase, corr = p, c

    if not phrase or not corr:
        await update.effective_message.reply_text(
            "Нужны две части: «фраза — перевод». Попробуй ещё раз через /teach? 🙂"
        )
        return ConversationHandler.END

    if _contains_bad_words(phrase) or _contains_bad_words(corr):
        await update.effective_message.reply_text("❌ Не сохранил: найден ненормативный контент.")
        return ConversationHandler.END

    add_glossary(update.effective_user.id, src, dst, phrase, corr)
    await update.effective_message.reply_text("✅ Готово. Ещё — /teach. Посмотреть — /glossary.")
    return ConversationHandler.END


async def glossary_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = get_glossary(update.effective_user.id)
    if not rows:
        await update.effective_message.reply_text(
            "Пока пусто. Добавь пары через /teach — и здесь появится твой мини-словарь. ✍️"
        )
        return
    lines = []
    for src, dst, phrase, corr in rows[:200]:
        lines.append(f"{src}→{dst}: {phrase} — {corr}")
    await update.effective_message.reply_text("\n".join(lines))


def build_teach_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler("teach", teach_start),
            CallbackQueryHandler(teach_start, pattern=r"^open:teach$"),  # клик из меню
        ],
        states={
            ASK_SRC_DST: [MessageHandler(filters.TEXT & ~filters.COMMAND, teach_src_dst)],
            ASK_LIST:    [MessageHandler(filters.TEXT & ~filters.COMMAND, teach_list)],
            ASK_CORR:    [MessageHandler(filters.TEXT & ~filters.COMMAND, teach_correction)],
        },  # ← ВАЖНО: закрываем фигурной скобкой
        fallbacks=[CommandHandler("cancel", lambda u, c: u.message.reply_text("Отменено"))],
        allow_reentry=True,
        per_message=False,
    )
