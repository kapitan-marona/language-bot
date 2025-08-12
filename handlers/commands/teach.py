from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from components.training_db import set_consent, has_consent, add_glossary, get_glossary

ASK_SRC_DST = 1
ASK_PHRASE = 2
ASK_CORR = 3

async def consent_on(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    set_consent(update.effective_user.id, True)
    await update.message.reply_text(
        "Спасибо! Режим корректировок включён. Используй /teach для добавления исправлений."
    )

async def consent_off(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    set_consent(update.effective_user.id, False)
    await update.message.reply_text("Режим корректировок выключен.")

async def teach_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not has_consent(update.effective_user.id):
        await update.message.reply_text("Сначала включи согласие на корректировки: /consent_on")
        return ConversationHandler.END
    await update.message.reply_text("Укажи направление в формате src→dst (например: en→ru):")
    return ASK_SRC_DST

async def teach_src_dst(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").lower().replace(" ", "")
    if "->" in text:
        src, dst = text.split("->", 1)
    elif "→" in text:
        src, dst = text.split("→", 1)
    else:
        await update.message.reply_text("Нужно в формате en→ru")
        return ASK_SRC_DST
    ctx.user_data["teach_src"] = src
    ctx.user_data["teach_dst"] = dst
    await update.message.reply_text("Введи фразу, которую нужно поправить:")
    return ASK_PHRASE

async def teach_phrase(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["teach_phrase"] = (update.message.text or "").strip()
    await update.message.reply_text("Как правильно её трактовать/переводить?")
    return ASK_CORR

async def teach_correction(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    src = ctx.user_data.get("teach_src")
    dst = ctx.user_data.get("teach_dst")
    phrase = ctx.user_data.get("teach_phrase")
    corr = (update.message.text or "").strip()
    add_glossary(update.effective_user.id, src, dst, phrase, corr)
    await update.message.reply_text("Супер, записал. Добавить ещё — /teach. Посмотреть — /glossary")
    return ConversationHandler.END

async def glossary_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = get_glossary(update.effective_user.id)
    if not rows:
        await update.message.reply_text("Пока пусто. Используй /teach чтобы добавить корректировку.")
        return
    lines = [f"{src}→{dst}: “{ph}” → “{cr}”" for src, dst, ph, cr in rows[:200]]
    await update.message.reply_text("Твои корректировки:\n" + "\n".join(lines))

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
