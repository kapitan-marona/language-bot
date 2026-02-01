# components/history.py
from collections import deque
from typing import Deque, Dict, Optional


def get_history(session: Dict, maxlen: int) -> Deque[dict]:
    hist = session.get("history")
    if isinstance(hist, deque):
        # если уже deque — убедимся, что maxlen выставлен
        if hist.maxlen != maxlen:
            hist = deque(list(hist)[-maxlen:], maxlen=maxlen)
            session["history"] = hist
        return hist

    if isinstance(hist, list):
        d = deque(hist[-maxlen:], maxlen=maxlen)
    else:
        d = deque(maxlen=maxlen)

    session["history"] = d
    return d


def append_history(session: Dict, role: str, content: str, maxlen: Optional[int] = None) -> None:
    """
    Append a message to session history.
    - If maxlen is provided, it becomes the current history limit for this session.
    - Otherwise uses session["_hist_maxlen"] (default: 40).
    """
    if isinstance(maxlen, int) and maxlen > 0:
        session["_hist_maxlen"] = maxlen

    effective_maxlen = int(session.get("_hist_maxlen", 40))
    d: deque = get_history(session, maxlen=effective_maxlen)
    d.append({"role": role, "content": content})
