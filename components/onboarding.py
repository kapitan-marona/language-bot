# ✅ Функция приветственного onboarding-сообщения для первого запуска

def get_onboarding_message(lang: str) -> str:
    messages = {
        "ru": (
            "👋 Привет! Добро пожаловать. Я — Мэтт, твой собеседник по языковой практике.\n\n"
            "🧠 Хочешь изменить стиль — только скажи.\n"
            "📈 Если будет слишком просто - дай знать.\n"
            "🎛 Я умею объяснять, переводить и шутить (иногда одновременно).\n\n"
            "🔔 И помни: я американец, могу ошибаться и говорить с акцентом 😅"
        ),
        "en": (
            "👋 Hey there! I'm Matt, your language practice buddy.\n\n"
            "🧠 Want to change the tone? I can do it.\n"
            "📈 Need a different level? Just tell me.\n"
            "🎛 I can explain, translate, and joke (sometimes all at once).\n\n"
            "🔔 Heads up: I’m American, so I might slip up or have an accent 😅"
        )
    }
    return messages.get(lang, messages["en"])

    
