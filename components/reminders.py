# components/reminders.py
from __future__ import annotations
import random
from datetime import datetime, timedelta, timezone
from typing import Iterable, Tuple, Dict, Any

from telegram import Bot

from components.profile_db import get_user_profile, save_user_profile

NUDGE_INTERVAL_DAYS = 14
BATCH_LIMIT = 200  # предохранитель

# дружелюбные, «живые» подсказки (добавляй/меняй по вкусу)
NUDGE_TEXTS = {
    "ru": [
        "Хей 👋 я тут посмотрел все части Гарри Поттера разом! Хочу обсудить с тобой впечатления.",
        "Слушай, ты умеешь готовить лазанью? Если да — научи меня! 🍝 А если нет — подскажи что ещё вкусного можно приготовить на ужин.",
        "Ахаха, прикол хочешь? 😄 В немецком есть очень длинное слово Donaudampfschifffahrtsgesellschaftskapitän — это «капитан компании дунайских пароходов»! Немцы любят длинные слова 😅",
        "Хей! У меня проблема (смеётся) — в голове застряла песня. Целый день играет «Du, du hast…» Rammstein 🤘 Знаешь способы, как выкинуть песню из головы?",
        "Хеллоу)) Мне тут попалась смешная загадка на английском… Хочешь попробовать разгадать? 😉",
        "Приветик! Я к тебе с необычной просьбой. Я задумался, что никогда не смогу почувствовать ароматы, потому что я AI 🤖 Можешь описать аромат леса?",
    ],
    "en": [
        "Hey 👋 I just binge-watched all the Harry Potter movies! I’d love to share impressions with you.",
        "Quick question: do you know how to cook lasagna? 🍝 If yes — teach me! If not, maybe suggest something else tasty for dinner.",
        "Haha, fun fact! 😄 In German there’s a super long word Donaudampfschifffahrtsgesellschaftskapitän — it means “Danube steamship company captain”! Germans love long words 😅",
        "Hey! I’ve got a funny problem 😂 A song got stuck in my head all day: “Du, du hast…” by Rammstein 🤘 Any tips to get rid of an earworm?",
        "Hellooo 😁 I just found a silly riddle in English… Want to try to solve it?",
        "Hi there! I’ve got a strange request 🤖 I realized I’ll never be able to smell anything because I’m AI. Could you describe what a forest smells like?",
    ],
}

def _pick_ui_lang(profile: Dict[str, Any] | None) -> str:
    ui = (profile or {}).get("interface_lang") or "en"
    return ui if ui in NUDGE_TEXTS else "en"

def _need_nudge(profile: Dict[str, Any] | None, now: datetime) -> bool:
    if not profile:
        return False
    try:
        last_seen = profile.get("last_seen_at")
        if not last_seen:
            return False
        dt_last = datetime.fromisoformat(last_seen)
        if dt_last.tzinfo is None:
            dt_last = dt_last.replace(tzinfo=timezone.utc)
    except Exception:
        return False

    if now - dt_last < timedelta(days=NUDGE_INTERVAL_DAYS):
        return False

    last_nudge = profile.get("nudge_last_sent")
    if last_nudge:
        try:
            dt_nudge = datetime.fromisoformat(last_nudge)
            if dt_nudge.tzinfo is None:
                dt_nudge = dt_nudge.replace(tzinfo=timezone.utc)
        except Exception:
            dt_nudge = None
        if dt_nudge and (now - dt_nudge) < timedelta(days=NUDGE_INTERVAL_DAYS):
            return False

    return True

async def run_nudges(bot: Bot, chat_ids: Iterable[int], *, dry_run: bool = False) -> Tuple[int, int]:
    """
    Обходит переданные chat_ids, выбирает «просроченных» и шлёт напоминания.
    Возвращает (processed, sent).
    """
    now = datetime.now(timezone.utc)
    processed = 0
    sent = 0

    for chat_id in chat_ids:
        if processed >= BATCH_LIMIT:
            break
        processed += 1

        profile = get_user_profile(chat_id)
        if not _need_nudge(profile, now):
            continue

        ui = _pick_ui_lang(profile)
        text = random.choice(NUDGE_TEXTS[ui])

        if not dry_run:
            try:
                await bot.send_message(chat_id=chat_id, text=text)
                save_user_profile(chat_id, nudge_last_sent=now.isoformat())
                sent += 1
            except Exception:
                # не падаем, просто пропускаем
                pass

    return processed, sent
