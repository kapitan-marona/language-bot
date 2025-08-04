from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from components.profile_db import save_user_gender
from components.levels import get_level_keyboard, LEVEL_PROMPT
from components.language import get_target_language_keyboard, TARGET_LANG_PROMPT
from components.mode import get_mode_keyboard, MODE_SWITCH_MESSAGES
from components.style import get_style_keyboard, get_intro_by_level_and_style, STYLE_LABEL_PROMPT
from components.onboarding import get_onboarding_message
from state.session import user_sessions
import random  # ✅ добавлено для выбора случайного шаблона

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
    async def proceed_onboarding(chat_id, session, context):
        stage = session.get("onboarding_stage")
        lang_code = session.get("interface_lang", "en")

        if stage == "awaiting_level":
            prompt = LEVEL_PROMPT.get(lang_code, LEVEL_PROMPT["en"])
            keyboard = get_level_keyboard()  # ✅ функция не принимает аргументы
            await context.bot.send_message(chat_id=chat_id, text=prompt, reply_markup=keyboard)  # ✅ keyboard уже содержит InlineKeyboardMarkup)

        elif stage == "awaiting_style":
            prompt = STYLE_LABEL_PROMPT.get(lang_code, STYLE_LABEL_PROMPT["en"])
            keyboard = get_style_keyboard()
            await context.bot.send_message(chat_id=chat_id, text=prompt, reply_markup=keyboard)

    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data

    # Всегда! Сначала инициализируем сессию пользователя
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}
    session = user_sessions[chat_id]

    # ✅ Удаление старого сообщения с кнопками
    await query.message.delete()

    # ✅ Подтверждающее сообщение и переход к следующему шагу
    if data.startswith("lang_"):
        lang_code = data.split("_")[1]
        session["interface_lang"] = lang_code
        session["onboarding_stage"] = "awaiting_level"
        await context.bot.send_message(
    chat_id=chat_id,
    text={
        "ru": f"Родной язык — {lang_code.upper()} ✅",
        "en": f"Native language — {lang_code.upper()} ✅"
    }.get(lang_code, f"Native language — {lang_code.upper()} ✅")
)
        await proceed_onboarding(chat_id, session, context)

    elif data.startswith("level_"):
        level = data.split("_")[1]
        session["level"] = level
        session["onboarding_stage"] = "awaiting_style"
        await context.bot.send_message(chat_id=chat_id, text=f"Level - {level} ✅")
        await proceed_onboarding(chat_id, session, context)

    elif data.startswith("style_"):
        style = data.split("_")[1]
        session["style"] = style
        session["onboarding_stage"] = "awaiting_target_lang"
        await context.bot.send_message(chat_id=chat_id, text=f"Style - {style.capitalize()} ✅")

        # ✅ Переход к выбору изучаемого языка
        lang = session.get("interface_lang", "en")
        prompt = TARGET_LANG_PROMPT.get(lang, TARGET_LANG_PROMPT["en"])
        keyboard = get_target_language_keyboard(lang)
        await context.bot.send_message(chat_id=chat_id, text=prompt, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("target_"):
        target_lang = data.split("_")[1]
        session["target_lang"] = target_lang
        session["onboarding_stage"] = "completed"
        await context.bot.send_message(chat_id=chat_id, text=f"Target language - {target_lang.upper()} ✅")
        await send_localized_onboarding(chat_id, session, context)

    elif data.startswith("gender_"):
        gender = data.split("_")[1]
        session["gender"] = gender
        await context.bot.send_message(chat_id=chat_id, text=f"Gender - {gender.capitalize()} ✅")

# ✅ Функция отправки онбординга (локализовано + вопрос)
async def send_localized_onboarding(chat_id, session, context):
    lang = session.get("interface_lang", "en")
    onboarding_text = get_onboarding_message(lang)
    await context.bot.send_message(chat_id=chat_id, text=onboarding_text)

    # ✅ Персональное приветствие на основе уровня и стиля
    level = session.get("level", "A1")
    style = session.get("style", "casual")
    intro = get_intro_by_level_and_style(level, style, lang)
    await context.bot.send_message(chat_id=chat_id, text=intro)

    # Переход к целевому языку + первый вопрос
    target_lang = session.get("target_lang", "sv")  # TODO: заменить на реальный выбор пользователя
    intro_message = {
        "ru": f"Давай попробуем поговорить на {target_lang.upper()}!",
        "en": f"Let's try speaking in {target_lang.upper()}!"
    }.get(lang, f"Let's switch to {target_lang.upper()}!")

    await context.bot.send_message(chat_id=chat_id, text=intro_message)

    first_questions = {
        "sv": [
            "Hej! Hur mår du idag?",
            "Ska vi börja prata svenska?",
            "Vad tycker du om svenska språket?",
            "Redo att öva svenska? 😄",
            "Berätta lite om dig själv på svenska!"
        ],
        "fi": [
            "Hei! Mitä kuuluu?",
            "Aloitetaanko suomeksi?",
            "Miten harjoittelet suomea?",
            "Puhutaanpa suomea!",
            "Kerro hieman itsestäsi suomeksi."
        ],
        "en": [
            "Hi! How are you today?",
            "Shall we start chatting in English?",
            "What do you think about practicing English?",
            "Are you ready for an English session? 😄",
            "Tell me a bit about yourself in English!"
        ],
        "es": [
            "¡Hola! ¿Cómo estás hoy?",
            "¿Empezamos a hablar en español?",
            "¿Qué opinas del idioma español?",
            "¿Listo para practicar español? 😄",
            "¡Cuéntame algo sobre ti en español!"
        ],
        "de": [
            "Hallo! Wie geht es dir heute?",
            "Wollen wir auf Deutsch anfangen?",
            "Was denkst du über die deutsche Sprache?",
            "Bereit, Deutsch zu üben? 😄",
            "Erzähl mir etwas über dich auf Deutsch!"
        ],
        "fr": [
            "Salut ! Comment tu vas aujourd'hui ?",
            "On commence en français ?",
            "Que penses-tu de la langue française ?",
            "Prêt à pratiquer le français ? 😄",
            "Parle-moi un peu de toi en français !"
        ],
        "ru": [
            "Привет! Как твои дела сегодня?",
            "Начнём говорить по-русски?",
            "Как тебе русский язык?",
            "Готов потренировать русский? 😄",
            "Расскажи немного о себе по-русски!"
        ]
    }
    prompt = random.choice(first_questions.get(target_lang, ["Let's begin!"]))
    await context.bot.send_message(chat_id=chat_id, text=prompt)
