"""Rage + a popping vein."""
import math

from ..painters import glare
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # rage (angry++)
    glare(d, x, y, w, h, 0.78, ir)


def _decor(d, W, H, now, ox=0.0, oy=0.0):  # a cross-shaped popping anger vein throbs by the brow -- furious
    cx, cy = 16 + int(ox), 8
    s = 5 + (math.sin(now * 9) + 1)                                               # throb 5..7
    for a in (45, 135, 225, 315):                                                # four inward chevrons (the cross)
        ax, ay = math.cos(math.radians(a)), math.sin(math.radians(a))
        ex, ey = cx + ax * s, cy + ay * s
        d.line([ex, ey, ex - ax * 3 - ay * 2, ey - ay * 3 + ax * 2], fill=1, width=1)
        d.line([ex, ey, ex - ax * 3 + ay * 2, ey - ay * 3 - ax * 2], fill=1, width=1)


MOOD = Mood("furious", dw=2, dh=2, paint=_paint, decor=_decor)
