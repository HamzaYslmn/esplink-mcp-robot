"""Caffeinated -- a steaming mug."""
import math

from ..spec import Mood


def _decor(d, W, H, now, ox=0.0, oy=0.0):  # a steaming mug, bottom-right -- "wired / caffeinated"
    cx, cy = W - 20, H - 11
    d.rounded_rectangle([cx, cy, cx + 12, cy + 9], radius=2, fill=1)              # cup body
    d.arc([cx + 11, cy + 1, cx + 17, cy + 8], start=-80, end=80, fill=1, width=2)  # handle
    for i in range(2):                                                            # two rising steam curls
        sx = cx + 3 + i * 6
        pts = [(sx + math.sin(f * 5 - now * 3) * 2.5, cy - 1 - f * 9) for f in (j / 6 for j in range(7))]
        d.line(pts, fill=1, width=1, joint="curve")


MOOD = Mood("wired", dw=2, dh=2, decor=_decor)
