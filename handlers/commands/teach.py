from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from components.training_db import set_consent, has_consent, add_glossary, get_glossary

ASK_SRC_DST = 1
ASK_PHRASE  = 2
ASK_CORR    = 3

def _split_pair(text: str):
    # поддержим разделители: " - ", " — ", " -> ", " → "
    for sep in [" — ", " - ", " -> ", " → "]:
        if sep in text:
            a, b = text.split(sep, 1)
            return a.strip(), b.strip()
    return None, None

async def consent_on(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    set_consent(update.effective_user.id, True)
    await update.message.reply_text(
        "Режим корректировок включён. Команда /teach:\n"
        "• Вариант 1 (коротко): сразу пришли пару «фраза — как правильно» (по умолчанию en→ru)\n"
        "• Вариант 2 (пошагово): укажи направление en→ru, затем фразу, затем исправление."
    )

async def consent_off(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    set_consent(update.effective_user.id, False)
    await update.message.reply_text("Режим корректировок выключен.")

async def teach_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not has_consent(update.effective_user.id):
        await update.message.reply_text("Сначала включи согласие: /consent_on")
        return ConversationHandler.END

    # Если пользователь сразу прислал «фраза — исправление», примем без лишних шагов
    t = (update.message.text or "").strip()
    if t and " " in t:
        phrase, corr = _split_pair(t)
        if phrase and corr:
            add_glossary(update.effective_user.id, "en", "ru", phrase, corr)
            await update.message.reply_text("✅ Записал. Ещё пример — снова /teach, список — /glossary.")
            return ConversationHandler.END

    await update.message.reply_text("Укажи направление в формате en→ru (или присылай сразу: «фраза — как правильно»).")
    return ASK_SRC_DST

async def teach_src_dst(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = (update.message.text or "").strip()

    # Если пользователь тут же прислал пару «фраза — исправление», тоже примем (дефолт en→ru)
    phrase, corr = _split_pair(t)
    if phrase and corr:
        add_glossary(update.effective_user.id, "en", "ru", phrase, corr)
        await update.message.reply_text("✅ Записал. Ещё пример — /teach, список — /glossary.")
        return ConversationHandler.END

    text = t.lower().replace(" ", "")
    if "->" in text:
        src, dst = text.split("->", 1)
    elif "→" in text:
        src, dst = text.split("→", 1)
    else:
        await update.message.reply_text("Нужно в формате en→ru или пришли сразу: «фраза — как правильно».")
        return ASK_SRC_DST

    ctx.user_data["teach_src"] = src
    ctx.user_data["teach_dst"] = dst
    await update.message.reply_text("Окей. Пришли фразу (без перевода).")
    return ASK_PHRASE

async def teach_phrase(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["teach_phrase"] = (update.message.text or "").strip()
    await update.message.reply_text("Теперь пришли, как правильно её трактовать/переводить.")
    return ASK_CORR

async def teach_correction(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    src = ctx.user_data.get("teach_src", "en")
    dst = ctx.user_data.get("teach_dst", "ru")
    phrase = ctx.user_data.get("teach_phrase")
    corr = (update.message.text or "").strip()
    if not phrase:
        # на случай, если пользователь прислал пару на последнем шаге
        p, c = _split_pair(corr)
        if p and c:
            phrase, corr = p, c
    add_glossary(update.effective_user.id, src, dst, phrase, corr)
    await update.message.reply_text("✅ Готово. Ещё — /teach. Посмотреть — /glossary.")
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
