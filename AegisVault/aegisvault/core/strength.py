"""Password strength heuristic (0..4)."""
from __future__ import annotations
import re

LABELS = ["Very Weak", "Weak", "Fair", "Strong", "Excellent"]
COLORS = ["#ff3b3b", "#ff7a3b", "#f5c542", "#3bd16f", "#00e5a8"]


def score(pw: str) -> int:
    if not pw:
        return 0
    s = 0
    if len(pw) >= 8: s += 1
    if len(pw) >= 14: s += 1
    classes = 0
    if re.search(r"[a-z]", pw): classes += 1
    if re.search(r"[A-Z]", pw): classes += 1
    if re.search(r"\d", pw): classes += 1
    if re.search(r"[^A-Za-z0-9]", pw): classes += 1
    s += max(0, classes - 1)
    return min(4, s)


def label(pw: str) -> tuple[int, str, str]:
    sc = score(pw)
    return sc, LABELS[sc], COLORS[sc]
