from telegram import Update
from telegram.ext import ContextTypes
from keyboards import voice_mode_button, text_mode_button
from prompts import rebuild_system_prompt

async def toggle_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vm = context.user_data.get("voice_mode", False)
    context.user_data["voice_mode"] = not vm

    rebuild_system_prompt(context)

    kb = text_mode_button if context.user_data["voice_mode"] else voice_mode_button
    msg = "🎤 Voice mode ON — теперь отвечаю голосом." if context.user_data["voice_mode"] else "⌨️ Text mode ON — вернулась к тексту."
    await update.message.reply_text(msg, reply_markup=kb)
