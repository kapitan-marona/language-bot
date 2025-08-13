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

async def teach_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not has_consent(update.effective_user.id):
        await update.effective_message.reply_text("Сначала включи согласие: /consent_on")
        return ConversationHandler.END

    t = (update.message.text or "").strip()
    if t and " " in t:
        phrase, corr = _split_pair(t)
        if phrase and corr:
            add_glossary(update.effective_user.id, "en", "ru", phrase, corr)
            await update.effective_message.reply_text("✅ Записал. Ещё пример — снова /teach, список — /glossary.")
            return ConversationHandler.END

    await update.effective_message.reply_text(
        "Укажи направление (en→ru / ru→en) или пришли пару сразу в формате «фраза — как правильно».")
    return ASK_SRC_DST

async def teach_src_dst(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = (update.message.text or "").strip()
    if t.lower() in ["en->ru", "en→ru", "en-ru", "en ru", "enru"]:
        ctx.user_data["teach_src"], ctx.user_data["teach_dst"] = "en", "ru"
    elif t.lower() in ["ru->en", "ru→en", "ru-en", "ru en", "ruen"]:
        ctx.user_data["teach_src"], ctx.user_data["teach_dst"] = "ru", "en"
    else:
        await update.effective_message.reply_text("Нужно указать en→ru или ru→en. Попробуй ещё раз.")
        return ASK_SRC_DST

    await update.effective_message.reply_text("Пришли исходную фразу (или сразу «фраза — как правильно»).")
    return ASK_PHRASE

async def teach_phrase(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = (update.message.text or "").strip()
    p, c = _split_pair(t)
    if p and c:
        ctx.user_data["teach_phrase"] = p
        await update.effective_message.reply_text("Теперь пришли корректировку (после «—»).")
        return ASK_CORR
    ctx.user_data["teach_phrase"] = t
    await update.effective_message.reply_text("Теперь пришли корректировку (как правильно).")
    return ASK_CORR

async def teach_correction(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    src = ctx.user_data.get("teach_src", "en")
    dst = ctx.user_data.get("teach_dst", "ru")
    phrase = ctx.user_data.get("teach_phrase")
    corr = (update.message.text or "").strip()
    if not phrase:
        p, c = _split_pair(corr)
        if p and c:
            phrase, corr = p, c
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
