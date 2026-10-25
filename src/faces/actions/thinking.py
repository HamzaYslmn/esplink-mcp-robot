"""Gaze up at nerdy tokens drifting overhead -- thinking."""
import math

from ..spec import Action

_TOKENS = ("E=mc^2", "a^2+b^2=c^2", "F=ma", "v=d/t", "2^10", "i^2=-1", "dx/dt",
           "3.14", "1.618", "9.8", "42", "404", "1337", "O(n)", "?")


def _formula(d, x, y, text):   # draw a short formula; a '^' raises the next char as a superscript
    cx = x
    for k, ch in enumerate(text):
        if ch == "^":
            continue
        sup = k > 0 and text[k - 1] == "^"
        d.text((cx, y - 3 if sup else y), ch, fill=1)
        cx += 4 if sup else 6


def _pose(now):   # gaze up at the floating symbols, slow wander
    return math.sin(now * 0.7) * 7, -9 + math.sin(now * 0.4) * 2, 1.0


def _overlay(d, W, H, now, ox=0.0, oy=0.0):  # nerdy tokens drift up -- "thinking" ('^' = superscript)
    for i in range(4):
        t = (now * 0.4 + i / 4) % 1.0                   # 0..1 rise progress
        y = H - 10 - t * (H - 16)                       # float up the screen
        ti = (i * 3 + int(now * 0.4 + i / 4)) % len(_TOKENS)
        x = 6 + i * (W - 50) / 3 + math.sin(now * 1.1 + i * 2) * 5
        _formula(d, x, y, _TOKENS[ti])


ACTION = Action("thinking", mood="focused", pose=_pose, overlay=_overlay)
