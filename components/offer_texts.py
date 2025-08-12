from __future__ import annotations

OFFER = {
    "reminder_after_10": {
        "ru": (
            "Кажется, ты разогрел(а) двигатели на полную — 🛫 уже 10 сообщений сегодня!\n"
            "Осталось 5 в пробном периоде. Премиум снимает ограничение — оформить на 30 дней можно за 149 ⭐ через /buy."
        ),
        "en": (
            "You’re on fire — 🛫 that’s 10 messages today!\n"
            "You’ve got 5 left on the trial. Go Premium (30 days for 149 ⭐) via /buy."
        ),
    },
    "limit_reached": {
        "ru": (
            "Ты сегодня сделал(а) 15 сообщений — лимит пробного дня достигнут.\n"
            "Хочешь без ограничений? 30 дней Премиум за 149 ⭐ — /buy\n"
            "Хочешь поддержать проект — /donate 🙌"
        ),
        "en": (
            "You’ve hit today’s 15-message limit.\n"
            "Go Premium for 30 days (149 ⭐) — /buy\n"
            "Or support the project — /donate 🙌"
        ),
    },
    "help_free_header": {
        "ru": "Помощь и навигация (бесплатный доступ)",
        "en": "Help & Navigation (free tier)",
    },
    "help_premium_header": {
        "ru": "Помощь и навигация (премиум)",
        "en": "Help & Navigation (premium)",
    },
    "help_body_common": {
        "ru": (
            "Команды:\n"
            "/buy — оформить доступ на 30 дней\n"
            "/donate — поддержать проект\n"
            "/promo — ввести промокод\n"
            "/lang — сменить язык интерфейса/практики\n"
            "/glossary — личные корректировки перевода\n"
        ),
        "en": (
            "Commands:\n"
            "/buy — get 30-day access\n"
            "/donate — support the project\n"
            "/promo — apply promo code\n"
            "/lang — change interface/practice language\n"
            "/glossary — your translation corrections\n"
        ),
    },
    "premium_card": {
        "ru": "🎟 Премиум активен до {date}. Сообщения сегодня: {used}/∞",
        "en": "🎟 Premium active until {date}. Messages today: {used}/∞",
    },
    "free_card": {
        "ru": "🔓 Бесплатный доступ. Сообщения сегодня: {used}/15",
        "en": "🔓 Free access. Messages today: {used}/15",
    },
}
