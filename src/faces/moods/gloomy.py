"""Downcast + a little rain cloud."""
from ..painters import brow
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # downcast droop
    brow(d, x, y, w, h, 0.30, 0.66, ir)


def _decor(d, W, H, now, ox=0.0, oy=0.0):  # a little rain cloud drizzles overhead -- "gloomy"
    cx, cy = W // 2 + int(ox), 7
    for dx, r in ((-7, 4), (0, 5), (7, 4)):                                       # three lumps + flat base
        d.ellipse([cx + dx - r, cy - r, cx + dx + r, cy + r], fill=1)
    d.rectangle([cx - 11, cy, cx + 11, cy + 3], fill=1)
    for i in range(4):                                                            # falling rain streaks
        t = (now * 1.5 + i / 4) % 1.0
        rx, ry = cx - 9 + i * 6, cy + 5 + t * 12
        d.line([rx, ry, rx - 1, ry + 3], fill=1, width=1)


MOOD = Mood("gloomy", dw=-2, dh=-4, paint=_paint, decor=_decor)
