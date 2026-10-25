"""Ghost -- see-through (dithered) eyes with a solid rim and a wavy sheet hem, wisps curling up off
them. Slightly narrow and tall, with a slow float."""
import math

from ..primitives import rand
from ..spec import Mood

_EYES = ((41, 32), (87, 32))                      # resting eye centres, before the gaze offset


def _paint(d, x, y, w, h, r, ir):                 # translucent body: punch a checkerboard inside the rim
    d.point([(xx, yy) for yy in range(int(y + 3), int(y + h - 2))
             for xx in range(int(x + 3), int(x + w - 2)) if (xx + yy) % 2], fill=0)
    for k in range(3):                            # three bites out of the bottom edge -> the sheet's hem
        bx = x + w * (k + 0.5) / 3
        d.ellipse([bx - w / 7, y + h - 5, bx + w / 7, y + h + 6], fill=0)


def _decor(d, W, H, now, ox=0.0, oy=0.0):         # wisps rising off the eyes, swaying as they go
    for i in range(6):
        u = (now * 0.3 + rand(i)) % 1.0
        cx, cy = _EYES[i % 2]
        x = cx + ox + (rand(i, 3) - 0.5) * 28 + math.sin(now * 2 + i) * 2
        if u < 0.8:
            d.point([(x, cy + oy - 18 - u * 14)], fill=1)


MOOD = Mood("ghost", dw=-4, dh=4, sway=(1.0, 1.1), paint=_paint, decor=_decor)
