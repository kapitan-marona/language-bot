from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from components.training_db import set_consent, has_consent, add_glossary, get_glossary

ASK_SRC_DST = 1
ASK_PHRASE  = 2
ASK_CORR    = 3

def _split_pair(text: str):
    for sep in [" — ", " - ", " -> ", " → "]:
        if sep in text:
            a, b = text.split(sep, 1)
            return a.strip(), b.strip()
    return None, None

# --------- СОГЛАСИЕ НА РЕЖИМ TEACH ----------
async def consent_on(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    set_consent(update.effective_user.id, True)
    await update.effective_message.reply_text(
        "Режим корректировок включён.\n\n"
        "Как использовать /teach:\n"
        "1) Укажи направление: en→ru или ru→en.\n"
        "2) Пришли исходную фразу — как ты её сказал/написал.\n"
        "3) Пришли корректировку — как правильно.\n\n"
        "Все твои правки сохраняются в /glossary. Отключить согласие: /consent_off."
    )

async def consent_off(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    set_consent(update.effective_user.id, False)
    await update.effective_message.reply_text("Режим корректировок выключен.")
# -------------------------------------------------------

async def teach_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not has_consent(update.effective_user.id):
        await update.effective_message.reply_text("Сначала включи согласие: /consent_on")
        return ConversationHandler.END

    # Переходим на пошаговый сценарий (направление → фраза → корректировка)
    await update.effective_message.reply_text(
        "Укажи направление: en→ru или ru→en.\n"
        "Затем пришли исходную фразу и отдельным сообщением — корректировку."
    )
    return ASK_SRC_DST

async def teach_src_dst(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = (update.message.text or "").strip().lower()
    if t in ["en->ru", "en→ru", "en-ru", "en ru", "enru"]:
        ctx.user_data["teach_src"], ctx.user_data["teach_dst"] = "en", "ru"
    elif t in ["ru->en", "ru→en", "ru-en", "ru en", "ruen"]:
        ctx.user_data["teach_src"], ctx.user_data["teach_dst"] = "ru", "en"
    else:
        await update.effective_message.reply_text("Нужно указать: en→ru или ru→en. Попробуй ещё раз.")
        return ASK_SRC_DST

    await update.effective_message.reply_text("Пришли исходную фразу — как ты её сказал/написал.")
    return ASK_PHRASE

async def teach_phrase(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = (update.message.text or "").strip()
    # Не рекламируем односообщенческий формат, но поддерживаем как удобный фолбэк
    p, c = _split_pair(t)
    if p and c:
        ctx.user_data["teach_phrase"] = p
        await update.effective_message.reply_text("Теперь пришли корректировку — как правильно.")
        return ASK_CORR

    ctx.user_data["teach_phrase"] = t
    await update.effective_message.reply_text("Теперь пришли корректировку — как правильно.")
    return ASK_CORR

async def teach_correction(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    src = ctx.user_data.get("teach_src", "en")
    dst = ctx.user_data.get("teach_dst", "ru")
    phrase = ctx.user_data.get("teach_phrase")
    corr = (update.message.text or "").strip()

    # Поддержка случая, когда на этом шаге прислали «фраза — корректировка»
    if not phrase:
        p, c = _split_pair(corr)
        if p and c:
            phrase, corr = p, c

    # Защита от пустых значений
    if not phrase or not corr:
        await update.effective_message.reply_text("Нужны две части: исходная фраза и корректировка. Попробуй ещё раз через /teach.")
        return ConversationHandler.END

    add_glossary(update.effective_user.id, src, dst, phrase, corr)
    await update.effective_message.reply_text("✅ Готово. Ещё — /teach. Посмотреть — /glossary.")
    return ConversationHandler.END

async def glossary_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = get_glossary(update.effective_user.id)
    if not rows:
        await update.effective_message.reply_text("Список пуст. Сначала добавь примеры через /teach.")
        return
    lines = []
    for src, dst, phrase, corr in rows[:50]:
        lines.append(f"{src}→{dst}: {phrase} — {corr}")
    await update.effective_message.reply_text("\n".join(lines))

def build_teach_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("teach", teach_start)],
        states={
            ASK_SRC_DST: [MessageHandler(filters.TEXT & ~filters.COMMAND, teach_src_dst)],
            ASK_PHRASE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, teach_phrase)],
            ASK_CORR:    [MessageHandler(filters.TEXT & ~filters.COMMAND, teach_correction)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: u.message.reply_text("Отменено"))],
        allow_reentry=True,
        per_message=False,
    )
