from components.language import get_language_keyboard, get_target_language_keyboard
from components.profile_db import save_user_profile, load_user_profile
from components.promo import check_promo_code, activate_promo  # 🟡 добавлено: для обработки промокодов
from components.texts import PROMO_ASK, PROMO_SUCCESS, PROMO_FAIL, PROMO_ALREADY_USED  # 🟡 добавлено: тексты


class Form:
    native_lang = "awaiting_native_lang"
    promo_code = "awaiting_promo_code"           # 🟡 добавлено: новое состояние для промокода
    target_lang = "awaiting_target_lang"
    style = "awaiting_style"
    gender = "awaiting_gender"


async def start_onboarding(message, state):
    await message.answer("⌨️ Подготовка... / ⌨️ Preparing...")
    await message.answer("Выбери язык интерфейса / Choose your interface language:",
                         reply_markup=get_language_keyboard())
    await state.set_state(Form.native_lang)


async def process_native_lang(message, state):
    lang = message.text.lower()
    await state.update_data(native_lang=lang)
    user_profile = load_user_profile(message.from_user.id)
    user_profile["native_lang"] = lang
    save_user_profile(message.from_user.id, user_profile)

    # 🟡 Вставка шага: запрос промокода
    prompt = PROMO_ASK.get(lang, PROMO_ASK["en"])
    await message.answer(prompt)
    await state.set_state(Form.promo_code)


async def process_promo_code(message, state):
    code_input = message.text.strip()
    user_profile = load_user_profile(message.from_user.id)
    lang = user_profile.get("native_lang", "en")

    if code_input.lower() in ["нет", "no"]:
        pass  # идем дальше
    elif user_profile.get("promo_code_used"):
        await message.answer(PROMO_ALREADY_USED.get(lang, PROMO_ALREADY_USED["en"]))
    else:
        success, result = activate_promo(user_profile, code_input)
        if success:
            save_user_profile(message.from_user.id, user_profile)
            await message.answer(PROMO_SUCCESS.get(lang, PROMO_SUCCESS["en"]))
        else:
            await message.answer(PROMO_FAIL.get(lang, PROMO_FAIL["en"]))

    await state.update_data(promo_checked=True)
    await message.answer("Выбери язык, который хочешь изучать / Choose the language you want to learn:",
                         reply_markup=get_target_language_keyboard(lang, user_profile))  # 🟡 передаём профиль
    await state.set_state(Form.target_lang)
