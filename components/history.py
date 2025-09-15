# components/history.py
from collections import deque
from typing import Deque, Dict

def get_history(session: Dict, maxlen: int) -> Deque[dict]:
    hist = session.get("history")
    if isinstance(hist, deque):
        return hist
    if isinstance(hist, list):
        d = deque(hist[-maxlen:], maxlen=maxlen)
    else:
        d = deque(maxlen=maxlen)
    session["history"] = d
    return d

def append_history(session: Dict, role: str, content: str) -> None:
    d: deque = get_history(session, maxlen=session.get("_hist_maxlen", 40))
    d.append({"role": role, "content": content})
