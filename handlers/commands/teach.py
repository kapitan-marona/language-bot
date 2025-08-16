from __future__ import annotations
import re
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from components.training_db import set_consent, has_consent, add_glossary, get_glossary
from components.i18n import get_ui_lang
from components.profile_db import get_user_profile
from handlers.chat.prompt_templates import INTRO_QUESTIONS

ASK_SRC_DST = 1
ASK_LIST    = 2
ASK_CORR    = 3  # fallback для одиночной пары (оставлен на случай старого поведения)

_SEP_VARIANTS = [" — ", " - ", " -> ", " → ", "—", "-", "->", "→"]

_LANG_PAIR_RE = re.compile(
    r"^\s*([A-Za-z]{2})\s*(?:-|—|->|→|\s)\s*([A-Za-z]{2})\s*$"
)

# Простейший фильтр ненормативной лексики (EN/RU).
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
    """
    Пара двухбуквенных кодов (ISO-639-1): en-ru, en-fi, ru-en, ru-es и т.д.
    Возвращает (src, dst) в нижнем регистре или (None, None).
    """
    m = _LANG_PAIR_RE.match((s or ""))
    if not m:
        return None, None
    return m.group(1).lower(), m.group(2).lower()

def _resume_kb(ui: str) -> InlineKeyboardMarkup:
    text = "▶️ Продолжить" if ui == "ru" else "▶️ Resume"
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data="TEACH:RESUME")]])

# ----- НОВОЕ: реплики Мэтта после «Продолжить/Resume» -----
RESUME_LINES = {
    "ru": [
        "Круто, что мы пополняем словарный запас друг друга — это честный обмен, почти алхимия ✨",
        "Спасибо за новое словечко ❤️ Так на чём мы остановились?",
        "Всю жизнь мы учимся новому — спасибо, что расширяешь мой словарь 🙌 Есть любимое слово?",
        "Классные примеры! Давай проверим их в деле — продолжим?",
        "С новыми знаниями — вперёд! Выберем тему: путешествия, фильмы или работа?",
    ],
    "en": [
        "Love that we’re trading vocabulary — fair exchange, almost like alchemy ✨",
        "Thanks for the new word ❤️ So, where did we leave off?",
        "We’re always learning — thanks for expanding my vocab 🙌 Do you have a favorite word?",
        "Great examples! Let’s put them to work — shall we keep going?",
        "Armed with new words — let’s roll! Pick a topic: travel, movies, or work?",
    ],
}

# --------- СОГЛАСИЕ НА РЕЖИМ TEACH ----------
async def consent_on(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    set_consent(update.effective_user.id, True)
    await update.effective_message.reply_text(
        "✅ Режим корректировок включён.\n\n"
        "Как пользоваться:\n"
        "1) Отправь языковую пару двумя буквами: en-ru, ru-en, en-fi… Если сомневаешься — /codes.\n"
        "2) Затем списком пришли строки «фраза — перевод», по одной на строку.\n\n"
        "Пример:\n"
        "I feel you — Понимаю тебя\n"
        "Break a leg — Удачи!\n\n"
        "Готово — я сохраню всё в /glossary. Спасибо! Ты делаешь Мэтта лучше ❤️"
    )

async def consent_off(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    set_consent(update.effective_user.id, False)
    await update.effective_message.reply_text("Окей, режим корректировок выключен. Вернёшься — скажи /consent_on 🙂")
# -------------------------------------------------------

async def teach_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not has_consent(update.effective_user.id):
        await update.effective_message.reply_text("Сначала включи согласие: /consent_on 🙂")
        return ConversationHandler.END

    # ❄️ Ставим паузу диалога Мэтта
    ctx.chat_data["dialog_paused"] = True

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
        "Принято! Теперь пришли список строк «фраза — перевод» (по одной на строку).\n"
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
        # fallback: одиночная строка без разделителя — просим корректный формат
        ctx.user_data["teach_phrase"] = block
        await update.effective_message.reply_text(
            "Нужен формат «фраза — перевод», по одной паре на строку. Попробуем ещё раз? 🙂"
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

    ui = get_ui_lang(update, ctx)

    if not saved and skipped_bad > 0:
        await update.effective_message.reply_text(
            "❌ Не сохранил: найден ненормативный контент. Давай без этого, ок? 😉",
            reply_markup=_resume_kb(ui),
        )
        return ConversationHandler.END

    if saved:
        header = "✅ Всё получилось, спасибо!\nВ глоссарий добавлено:\n"
        body = "\n".join(saved[:50])
        footer = "\n\nЕщё примеры — снова /teach. Или вернёмся к разговору:"
        if skipped_bad:
            footer += f"\n(Пропущено из-за ненормативной лексики: {skipped_bad})"
        await update.effective_message.reply_text(header + body + footer, reply_markup=_resume_kb(ui))
    else:
        await update.effective_message.reply_text(
            "Я не увидел пар «фраза — перевод». Пришли их по одной на строку.\n"
            "Например: I feel you — Понимаю тебя 🙂",
            reply_markup=_resume_kb(ui),
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

    ui = get_ui_lang(update, ctx)

    if not phrase or not corr:
        await update.effective_message.reply_text(
            "Нужны две части: «фраза — перевод». Попробуй ещё раз через /teach? 🙂",
            reply_markup=_resume_kb(ui),
        )
        return ConversationHandler.END

    if _contains_bad_words(phrase) or _contains_bad_words(corr):
        await update.effective_message.reply_text("❌ Не сохранил: найден ненормативный контент.", reply_markup=_resume_kb(ui))
        return ConversationHandler.END

    add_glossary(update.effective_user.id, src, dst, phrase, corr)
    await update.effective_message.reply_text("✅ Готово. Ещё — /teach. Или вернёмся к разговору:", reply_markup=_resume_kb(ui))
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

# ---------- КНОПКА «ПРОДОЛЖИТЬ» (снять паузу) ----------
async def resume_chat_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ui = get_ui_lang(update, ctx)
    ctx.chat_data["dialog_paused"] = False
    await update.callback_query.answer("OK")

    profile = get_user_profile(update.effective_user.id) or {}
    tgt = (profile.get("target_lang") or "en").lower()

    # Если есть набор реплик для целевого языка — используем его, иначе fallback на INTRO_QUESTIONS
    if tgt in RESUME_LINES:
        line = random.choice(RESUME_LINES[tgt])
        await update.effective_message.reply_text(line)
    else:
        question = random.choice(INTRO_QUESTIONS.get(tgt, INTRO_QUESTIONS.get("en", ["So, shall we continue?"])))
        pre = "Продолжаем! " if ui == "ru" else "Back to chat! "
        await update.effective_message.reply_text(pre + question)

def build_teach_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("teach", teach_start)],
        states={
            ASK_SRC_DST: [MessageHandler(filters.TEXT & ~filters.COMMAND, teach_src_dst)],
            ASK_LIST:    [MessageHandler(filters.TEXT & ~filters.COMMAND, teach_list)],
            ASK_CORR:    [MessageHandler(filters.TEXT & ~filters.COMMAND, teach_correction)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: u.message.reply_text("Отменено"))],
        allow_reentry=True,
        per_message=False,
    )
