from __future__ import annotations
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from components.how_to_pay_game import HOW_TO_PAY_GAME

def _lang(ctx: ContextTypes.DEFAULT_TYPE) -> str:
    return ctx.user_data.get("ui_lang", "ru")

async def how_to_pay_entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = _lang(ctx)
    q = update.callback_query
    await q.answer()
    await q.message.reply_text(HOW_TO_PAY_GAME["stage_intro"][lang])
    await q.message.chat.send_message(
        HOW_TO_PAY_GAME["stage_intro_reply"][lang],
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Ок, выйти" if lang == "ru" else "Ok. Back to menu", callback_data="htp_exit"),
            InlineKeyboardButton(HOW_TO_PAY_GAME["stage_how"][lang], callback_data="htp_how"),
        ]])
    )

async def how_to_pay_how(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = _lang(ctx)
    q = update.callback_query
    await q.answer()
    await q.message.reply_markdown(
        HOW_TO_PAY_GAME["stage_how_reply"][lang],
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Ок, остаться free" if lang == "ru" else "Ok. Stay for free", callback_data="htp_exit"),
            InlineKeyboardButton("Понял, пошёл добывать ⭐" if lang == "ru" else "Got it, going to get ⭐", callback_data="htp_buy"),
        ]])
    )

async def how_to_pay_exit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from handlers.commands.help import help_command
    await update.callback_query.answer()
    return await help_command(update, ctx)

async def how_to_pay_go_buy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from handlers.commands.payments import buy_command
    await update.callback_query.answer()
    return await buy_command(update, ctx)
