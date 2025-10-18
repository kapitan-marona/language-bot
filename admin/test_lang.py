# admin/test_lang.py
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from utils.decorators import safe_handler

from handlers.chat.prompt_templates import pick_intro_question
from components.translator import do_translate
from components.voice import synthesize_voice

import logging
import os

logger = logging.getLogger(__name__)


@safe_handler
async def test_lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Тестирует новый язык: генерирует пример фразы, перевод и озвучку.
    Использование:
      /test_lang it   — итальянский
      /test_lang pt   — португальский (🇧🇷 вариант)
    """
    chat_id = update.effective_chat.id
    args = context.args or []

    if not args:
        await update.message.reply_text(
            "⚙️ Использование: /test_lang <код_языка>\n"
            "Примеры:\n"
            "• /test_lang it — 🇮🇹 Italiano\n"
            "• /test_lang pt — 🇧🇷 Português (Brasil)"
        )
        return

    lang_code = args[0].lower().strip()
    level = "A2"
    style = "casual"

    await update.message.reply_text(
        f"🧪 Тестирование нового языка: `{lang_code}`", parse_mode="Markdown"
    )

    try:
        # 1️⃣ Генерируем вступительную фразу
        question = pick_intro_question(level=level, style=style, lang=lang_code)
        await context.bot.send_message(chat_id=chat_id, text=f"🗣️ Пример фразы:\n{question}")

        # 2️⃣ Перевод (на русский)
        translation = await do_translate(
            text=question,
            interface_lang="ru",
            target_lang=lang_code,
            direction="target→ui",
            style=style,
            level=level,
        )
        await context.bot.send_message(chat_id=chat_id, text=f"💬 Перевод:\n{translation}")

        # 3️⃣ Озвучка (TTS)
        try:
            audio_path = synthesize_voice(
                text=question,
                language_code=lang_code,
                style=style,
                level=level,
            )

            if audio_path and os.path.exists(audio_path):
                with open(audio_path, "rb") as f:
                    await context.bot.send_voice(chat_id=chat_id, voice=f)
                os.remove(audio_path)
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="🎧 Озвучка недоступна для этого языка.",
                )
        except Exception as e:
            logger.exception("TTS test failed")
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Ошибка озвучки: {e}")

        await context.bot.send_message(chat_id=chat_id, text="✅ Тест завершён успешно.")

    except Exception as e:
        logger.exception("test_lang_command failed")
        await update.message.reply_text(f"❌ Ошибка: {e}")


# Функция для регистрации команды (если ты используешь register_admin_handlers)
def register_test_lang(application):
    application.add_handler(CommandHandler("test_lang", test_lang_command))
