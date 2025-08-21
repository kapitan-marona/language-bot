# components/code_switch.py
from __future__ import annotations
import json, re, logging
from typing import Tuple, List, Dict
from components.gpt_client import ask_gpt

log = logging.getLogger(__name__)

# Базовые детекторы: кириллица/латиница
_CYRILLIC = re.compile(r"[А-Яа-яЁё]")
_LATIN    = re.compile(r"[A-Za-z]")

def _need_fix(user_text: str, ui: str, tgt: str) -> bool:
    """
    Нужна ли «починка» смешанного ввода для пары ui↔target.
    Сейчас покрыты ru<->en. Другие пары можно расширить аналогично.
    """
    t = user_text or ""
    ui = (ui or "").lower()
    tgt = (tgt or "").lower()
    if ui == tgt:
        return False
    if ui == "ru" and tgt == "en":
        return bool(_CYRILLIC.search(t))
    if ui == "en" and tgt == "ru":
        return bool(_LATIN.search(t))
    return False

def _strip_code_fences(s: str) -> str:
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", (s or "").strip())

def _bold_once(haystack: str, needle: str) -> str:
    if not needle:
        return haystack
    # жирним первое точное совпадение по слову
    return re.sub(rf"\b{re.escape(needle)}\b", r"<b>\g<0></b>", haystack, count=1)

async def rewrite_mixed_input(
    user_text: str,
    ui_lang: str,
    target_lang: str,
) -> Tuple[str, str]:
    """
    Возвращает (clean_text, preface_html).
    clean_text — переформулированный текст ПОЛНОСТЬЮ на target_lang (для основного промпта).
    preface_html — короткая приставка на языке интерфейса с выделением замен жирным.
    Если исправления не нужны — (исходный_текст, "").
    """
    if not _need_fix(user_text, ui_lang, target_lang):
        return user_text, ""

    system = (
        "You are a precise rewriter for code-switched messages.\n"
        "Rewrite the user's text fully in the TARGET language, preserving meaning and tone.\n"
        "Also return a list of replacements for fragments not in the target language.\n"
        "Respond ONLY with strict JSON:\n"
        "{ \"rewritten\": string, \"replacements\": [ {\"src\": string, \"dst\": string} ] }"
    )
    user = f"TARGET={target_lang}\nTEXT={user_text}"

    try:
        raw = await ask_gpt(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            model="gpt-4o-mini"
        )
        data = json.loads(_strip_code_fences(raw))
        rewritten: str = (data.get("rewritten") or "").strip() or user_text
        replacements: List[Dict[str, str]] = data.get("replacements") or []
    except Exception:
        log.exception("codeswitch: parse failed")
        return user_text, ""

    # Подсветим заменённые фрагменты в переписанной фразе
    highlighted = rewritten
    for r in replacements:
        dst = (r.get("dst") or "").strip()
        highlighted = _bold_once(highlighted, dst)

    if (ui_lang or "").lower() == "ru":
        preface = f"Понял(а)! Ты имел(а) в виду: {highlighted}"
    else:
        preface = f"Got it! You meant: {highlighted}"

    return rewritten, preface
