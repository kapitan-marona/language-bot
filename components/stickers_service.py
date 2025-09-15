# components/stickers_service.py
import logging
import random
import re
from html import unescape
from typing import Dict, List, Optional

from telegram import Update
from telegram.ext import ContextTypes

from components.stickers import STICKERS_CONFIG, STICKERS_PRIORITY

logger = logging.getLogger(__name__)

def _normalize_for_triggers(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^\w\s\u0400-\u04FF\u00C0-\u024F]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _match_sticker_key(user_raw: str) -> Optional[str]:
    raw = user_raw or ""
    norm = _normalize_for_triggers(raw)
    for key in STICKERS_PRIORITY:
        cfg = STICKERS_CONFIG.get(key) or {}
        for emo in cfg.get("emoji", []):
            if emo and emo in raw:
                return key
        for trig in cfg.get("triggers", []):
            t = _normalize_for_triggers(trig)
            if t and t in norm:
                return key
    return None

async def maybe_send_thematic_sticker(context: ContextTypes.DEFAULT_TYPE, update: Update, session: Dict, history: List[dict], user_text: str):
    """
    Антифлуд: не больше 1 стикера в окне из 40 реплик истории.
    Вероятность: 30% при сработавшем триггере.
    """
    last_idx = session.get("last_sticker_hist_idx")
    hist_len = len(history or [])
    if isinstance(last_idx, int) and (hist_len - last_idx) < 40:
        return

    key = _match_sticker_key(user_text)
    if not key:
        return

    if random.random() >= 0.30:
        return

    file_id = (STICKERS_CONFIG.get(key) or {}).get("id")
    if not file_id:
        return
    try:
        await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=file_id)
        session["last_sticker_hist_idx"] = hist_len
    except Exception:
        logger.debug("send_sticker failed", exc_info=True)
