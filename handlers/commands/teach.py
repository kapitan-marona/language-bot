# handlers/commands/teach.py
from __future__ import annotations
import re
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from components.training_db import set_consent, has_consent, add_glossary, get_glossary
from components.i18n import get_ui_lang  # определяем язык интерфейса пользователя

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

# --- Триггеры выхода (принимаем оба языка, чтобы сработало при любом UI) ---
RU_EXIT_BTN = "⏹ Выйти из режима обучения"
EN_EXIT_BTN = "⏹ Exit teaching mode"

_EXIT_TEXTS = {
    RU_EXIT_BTN.lower(),
    EN_EXIT_BTN.lower(),
    # Русские варианты
    "выйти", "выход", "стоп",
    "выйти из teach", "выйти из режима обучения",
    # Английские варианты
    "exit", "quit", "stop",
    "exit teach", "exit teaching mode",
    # Команды
    "/teach_exit", "/cancel",
}

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


def _exit_button_text(ui: str) -> str:
    return EN_EXIT_BTN if ui == "en" else RU_EXIT_BTN


def _exit_keyboard(ui: str):
    return ReplyKeyboardMarkup(
        [[KeyboardButton(text=_exit_button_text(ui))]],
        resize_keyboard=True,
        one_time_keyboard=False
    )


def _is_exit_text(s: str) -> bool:
    return (s or "").strip().lower() in _EXIT_TEXTS


# --------- СОГЛАСИЕ НА РЕЖИМ TEACH ----------
async def consent_on(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, ctx)
    set_consent(update.effective_user.id, True)
    if ui == "en":
        msg = (
            "✅ Teaching mode is ON.\n\n"
            "How to use:\n"
            "1) Send a two-letter language pair: en-ru, ru-en, en-fi… If unsure — /codes.\n"
            "2) Then send lines of “phrase — translation”, one per line.\n\n"
            "Important: two separate messages — first the language pair, wait for confirmation, then the list.\n\n"
            "Example:\n"
            "I feel you — I understand you\n"
            "Break a leg — Good luck!\n\n"
            "I’ll save everything to /glossary.\n"
            "Thanks! You’re making Matt better ❤️"
        )
    else:
        msg = (
            "✅ Режим корректировок включён.\n\n"
            "Как пользоваться:\n"
            "1) Отправь языковую пару двумя буквами: en-ru, ru-en, en-fi… Если сомневаешься — /codes.\n"
            "2) Затем списком пришли строки «фраза — перевод», по одной на строке.\n\n"
            "Важно: это два разных сообщения — сначала пара языков, жди подтверждения, потом список пар.\n\n"
            "Пример:\n"
            "I feel you — Понимаю тебя\n"
            "Break a leg — Удачи!\n\n"
            "Я сохраню всё в /glossary.\n"
            "Спасибо! Ты делаешь Мэтта лучше ❤️"
        )
    await update.effective_message.reply_text(msg)


async def consent_off(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, ctx)
    set_consent(update.effective_user.id, False)
    msg = (
        "Teaching mode is OFF. When you want it back — use /consent_on 🙂"
        if ui == "en"
        else "Окей, режим корректировок выключен. Вернёшься — скажи /consent_on 🙂"
    )
    await update.effective_message.reply_text(msg)


# --------- ВХОД В РЕЖИМ TEACH ----------
async def teach_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, ctx)
    if not has_consent(update.effective_user.id):
        await update.effective_message.reply_text(
            "Please enable consent first: /consent_on 🙂" if ui == "en" else "Сначала включи согласие: /consent_on 🙂"
        )
        return ConversationHandler.END

    q = getattr(update, "callback_query", None)
    if q:
        try:
            await q.answer()
        except Exception:
            pass

    if ui == "en":
        msg = (
            "🎓 Teaching mode enabled.\n\n"
            "1) Send a language pair (e.g., en-ru or ru-en).\n"
            "2) Then send lines of “phrase — translation”, one per line.\n\n"
            f"To exit — press “{_exit_button_text(ui)}” or send /teach_exit."
        )
    else:
        msg = (
            "🎓 Режим обучения включён.\n\n"
            "1) Отправь языковую пару (например, en-ru или ru-en).\n"
            "2) Затем списком пришли строки «фраза — перевод», по одной на строке.\n\n"
            f"Чтобы выйти — нажми «{_exit_button_text(ui)}» или отправь /teach_exit."
        )

    await update.effective_message.reply_text(msg, reply_markup=_exit_keyboard(ui))
    return ASK_SRC_DST


async def _maybe_exit(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    """Возвращает True, если это команда/кнопка выхода, и уже ответил пользователю."""
    ui = get_ui_lang(update, ctx)
    t = (update.effective_message.text or "").strip()
    if _is_exit_text(t):
        await update.effective_message.reply_text(
            "⏹ Teaching mode is OFF. Back to normal chat."
            if ui == "en"
            else "⏹ Режим обучения выключен. Возвращаю обычный диалог.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return True
    return False


async def teach_src_dst(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, ctx)
    if await _maybe_exit(update, ctx):
        return ConversationHandler.END

    t = (update.message.text or "").strip()
    src, dst = _parse_lang_pair(t)
    if not src or not dst:
        msg = (
            "Please provide a pair of two-letter codes: en-ru, en-fi, ru-en, ru-es, etc. Try again? 🙂\n"
            "See language codes: /codes"
            if ui == "en"
            else "Нужно указать пару двухбуквенных кодов: en-ru, en-fi, ru-en, ru-es и т.д. Попробуешь ещё раз? 🙂\n"
                 "Подсказка по кодам — /codes"
        )
        await update.effective_message.reply_text(msg, reply_markup=_exit_keyboard(ui))
        return ASK_SRC_DST

    ctx.user_data["teach_src"], ctx.user_data["teach_dst"] = src, dst
    msg = (
        "Got it! Now send lines of “phrase — translation”, one per line.\n"
        "For example:\n"
        "I feel you — I understand you\n"
        "Break a leg — Good luck!"
        if ui == "en"
        else "Принято! Теперь пришли список строк «фраза — перевод» (по одной на строке).\n"
             "Например:\n"
             "I feel you — Понимаю тебя\n"
             "Break a leg — Удачи!"
    )
    await update.effective_message.reply_text(msg, reply_markup=_exit_keyboard(ui))
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
    ui = get_ui_lang(update, ctx)
    if await _maybe_exit(update, ctx):
        return ConversationHandler.END

    src = ctx.user_data.get("teach_src", "en")
    dst = ctx.user_data.get("teach_dst", "ru")
    block = (update.message.text or "").strip()

    pairs = _parse_pairs_block(block)

    if not pairs:
        ctx.user_data["teach_phrase"] = block
        msg = (
            "Expected the format “phrase — translation”, one pair per line. Try again? 🙂"
            if ui == "en"
            else "Нужен формат «фраза — перевод», по одной паре на строке. Попробуем ещё раз? 🙂"
        )
        await update.effective_message.reply_text(msg, reply_markup=_exit_keyboard(ui))
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
        msg = (
            "❌ Nothing saved: found inappropriate content. Let’s avoid that, ok? 😉"
            if ui == "en"
            else "❌ Не сохранил: найден ненормативный контент. Давай без этого, ок? 😉"
        )
        await update.effective_message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    if saved:
        if ui == "en":
            header = "✅ All set, thank you!\nAdded to glossary:\n"
            footer = "\n\nMore examples — run /teach again. View — /glossary."
            if skipped_bad:
                footer += f"\n(Skipped due to inappropriate content: {skipped_bad})"
        else:
            header = "✅ Всё получилось, спасибо!\nВ глоссарий добавлено:\n"
            footer = "\n\nЕщё примеры — снова /teach. Посмотреть — /glossary."
            if skipped_bad:
                footer += f"\n(Пропущено из-за ненормативной лексики: {skipped_bad})"

        body = "\n".join(saved[:50])
        await update.effective_message.reply_text(header + body + footer, reply_markup=ReplyKeyboardRemove())
    else:
        msg = (
            "I didn’t see any “phrase — translation” pairs. Please send them one per line.\n"
            "For example: I feel you — I understand you 🙂"
            if ui == "en"
            else "Я не увидел пар «фраза — перевод». Пришли их по одной на строке.\n"
                 "Например: I feel you — Понимаю тебя 🙂"
        )
        await update.effective_message.reply_text(msg, reply_markup=_exit_keyboard(ui))

    return ConversationHandler.END


async def teach_correction(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, ctx)
    if await _maybe_exit(update, ctx):
        return ConversationHandler.END

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
        msg = (
            "Two parts are required: “phrase — translation”. Try again via /teach 🙂"
            if ui == "en"
            else "Нужны две части: «фраза — перевод». Попробуй ещё раз через /teach? 🙂"
        )
        await update.effective_message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    if _contains_bad_words(phrase) or _contains_bad_words(corr):
        msg = "❌ Not saved: inappropriate content." if ui == "en" else "❌ Не сохранил: найден ненормативный контент."
        await update.effective_message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    add_glossary(update.effective_user.id, src, dst, phrase, corr)
    msg = "✅ Done. More — /teach. View — /glossary." if ui == "en" else "✅ Готово. Ещё — /teach. Посмотреть — /glossary."
    await update.effective_message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def glossary_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, ctx)
    rows = get_glossary(update.effective_user.id)
    if not rows:
        msg = (
            "Empty so far. Add pairs via /teach — and your mini-dictionary will appear here. ✍️"
            if ui == "en"
            else "Пока пусто. Добавь пары через /teach — и здесь появится твой мини-словарь. ✍️"
        )
        await update.effective_message.reply_text(msg)
        return
    lines = []
    for src, dst, phrase, corr in rows[:200]:
        lines.append(f"{src}→{dst}: {phrase} — {corr}")
    await update.effective_message.reply_text("\n".join(lines))


def build_teach_handler():
    """
    ConversationHandler с собственными состояниями.
    Регистрируется в dispatcher с block=True (в english_bot.py),
    чтобы обновления, попавшие в teach, не шли в общую логику чата.
    """
    exit_filter = filters.Regex("^(" + "|".join(map(re.escape, _EXIT_TEXTS)) + r")\s*$")

    return ConversationHandler(
        entry_points=[
            CommandHandler("teach", teach_start),
            CallbackQueryHandler(teach_start, pattern=r"^open:teach$"),  # клик из меню
        ],
        states={
            ASK_SRC_DST: [
                MessageHandler(exit_filter, teach_correction),  # мгновенный выход (обработается _maybe_exit)
                MessageHandler(filters.TEXT & ~filters.COMMAND, teach_src_dst),
            ],
            ASK_LIST: [
                MessageHandler(exit_filter, teach_correction),
                MessageHandler(filters.TEXT & ~filters.COMMAND, teach_list),
            ],
            ASK_CORR: [
                MessageHandler(exit_filter, teach_correction),
                MessageHandler(filters.TEXT & ~filters.COMMAND, teach_correction),
            ],
        },
        fallbacks=[
            CommandHandler("teach_exit", teach_correction),  # обработаем как выход
            CommandHandler("cancel", teach_correction),
        ],
        allow_reentry=True,
        per_message=False,
    )
