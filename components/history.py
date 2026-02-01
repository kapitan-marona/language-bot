# components/history.py
from collections import deque
from typing import Deque, Dict, Optional


def get_history(session: Dict, maxlen: int) -> Deque[dict]:
    hist = session.get("history")

    # If already deque but with different maxlen, rebuild
    if isinstance(hist, deque):
        if hist.maxlen != maxlen:
            d = deque(list(hist)[-maxlen:], maxlen=maxlen)
            session["history"] = d
            return d
        return hist

    if isinstance(hist, list):
        d = deque(hist[-maxlen:], maxlen=maxlen)
    else:
        d = deque(maxlen=maxlen)

    session["history"] = d
    return d


def append_history(session: Dict, role: str, content: str, maxlen: Optional[int] = None) -> None:
    # Save desired maxlen in session (used as default for future calls)
    if isinstance(maxlen, int) and maxlen > 0:
        session["_hist_maxlen"] = maxlen

    d: deque = get_history(session, maxlen=session.get("_hist_maxlen", 40))
    d.append({"role": role, "content": content})
