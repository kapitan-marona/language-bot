from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from components.profile_db import save_user_gender
from components.levels import get_level_keyboard, LEVEL_PROMPT
from components.language import get_target_language_keyboard, TARGET_LANG_PROMPT
from components.mode import get_mode_keyboard, MODE_SWITCH_MESSAGES
from components.style import get_style_keyboard, get_intro_by_level_and_style, STYLE_PROMPT, STYLE_LABEL_PROMPT
from components.onboarding import get_onboarding_message
from state.session import user_sessions

def get_gender_prompt_and_keyboard(lang_code):
    if lang_code == "ru":
        return (
            "Спрошу форму обращения к тебе сразу, чтобы избежать неловких ситуаций 😅",
            [
                [InlineKeyboardButton("муж", callback_data="gender_male"),
                 InlineKeyboardButton("жен", callback_data="gender_female"),
                 InlineKeyboardButton("друг", callback_data="gender_friend")]
            ]
        )
    else:
        return (
            "I’ll ask how to address you right away to avoid any awkward moments 😅",
            [
                [InlineKeyboardButton("male", callback_data="gender_male"),
                 InlineKeyboardButton("female", callback_data="gender_female"),
                 InlineKeyboardButton("friend", callback_data="gender_friend")]
            ]
        )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data

    # Всегда! Сначала инициализируем сессию пользователя
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}
    session = user_sessions[chat_id]

    # -- Логика выбора языка интерфейса (и формы обращения, если надо) --
    if data.startswith("lang_"):
        lang_code = data.split("_")[1]
        session["interface_lang"] = lang_code
        session["mode"] = "text"

        # --- Если пол уже выбран, сразу продолжаем flow ---
        from components.profile_db import get_user_gender
        if get_user_gender(chat_id):
            prompt = TARGET_LANG_PROMPT.get(lang_code, TARGET_LANG_PROMPT["en"])
            await query.message.reply_text(prompt, reply_markup=get_target_language_keyboard())
            return

        # --- Если не выбран — спрашиваем форму обращения ---
        gender_prompt, gender_keyboard = get_gender_prompt_and_keyboard(lang_code)
        await query.message.reply_text(
            gender_prompt,
            reply_markup=InlineKeyboardMarkup(gender_keyboard)
        )
        return

    # -- Логика выбора формы обращения --
    elif data in ["gender_male", "gender_female", "gender_friend"]:
        gender_map = {
            "gender_male": "male",
            "gender_female": "female",
            "gender_friend": "friend"
        }
        save_user_gender(chat_id, gender_map[data])

        # После выбора гендера — спрашиваем целевой язык
        # Безопасно получаем язык, если его вдруг нет — используем "en"!
        interface_lang = session.get("interface_lang", "en")
        prompt = TARGET_LANG_PROMPT.get(interface_lang, TARGET_LANG_PROMPT["en"])
        await query.message.reply_text(prompt, reply_markup=get_target_language_keyboard())
        return

    elif data.startswith("target_"):
        target_code = data.split("_")[1]
        session["target_lang"] = target_code

        interface_lang = session.get("interface_lang", "en")
        level_prompt = LEVEL_PROMPT.get(interface_lang, LEVEL_PROMPT["en"])
        await query.message.reply_text(level_prompt, reply_markup=get_level_keyboard())

    elif data.startswith("level_"):
        level = data.split("_")[1]
        session["level"] = level

        interface_lang = session.get("interface_lang", "en")
        await query.message.reply_text(get_onboarding_message(interface_lang))
        label_prompt = STYLE_LABEL_PROMPT.get(interface_lang, STYLE_LABEL_PROMPT["en"])
        await query.message.reply_text(label_prompt, reply_markup=get_style_keyboard())

    elif data.startswith("style_"):
        chosen_style = data.split("_")[1]
        session["style"] = chosen_style
        interface_lang = session.get("interface_lang", "en")
        level = session.get("level", "A1")
        intro = get_intro_by_level_and_style(level, chosen_style, interface_lang)
        await query.message.reply_text(intro)   # <<=== reply_markup убрали!


