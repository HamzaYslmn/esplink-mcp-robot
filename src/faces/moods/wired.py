"""Wired -- one coffee too many. The eyes are a touch too wide and never quite still: a fine
caffeine tremor, and every few seconds a twitch -- one eyelid flutters (the top of that eye
flickers down and back, a caffeine eyelid twitch) while stress marks flash at its corner. The
mug in the corner trembles with Pip, its coffee sloshing; its steam rises in two curls that widen
and thin out."""
import math

from ..primitives import rand
from ..spec import Mood

_EYES = ((41, 32), (87, 32))                      # resting eye centres, before the gaze offset
_HALF = 20                                        # eye half-size with dw=dh=3 (+ a pixel of margin)
_TWITCH = 3.0                                     # s per twitch window


def _twitch(now):
    """(strength 0..1, eye index) of the current twitch, if one is happening."""
    j = int(now / _TWITCH)
    t0 = j * _TWITCH + rand(j, 8) * (_TWITCH - 0.5)
    if rand(j, 7) < 0.7 and t0 <= now < t0 + 0.45:
        return 1.0 - (now - t0) / 0.45, int(rand(j, 9) * 2)
    return 0.0, 0


def _decor(d, W, H, now, ox=0.0, oy=0.0):
    tw, side = _twitch(now)
    if tw:
        ex, ey = _EYES[side][0] + ox, _EYES[side][1] + oy
        lid = (2 + 5 * tw) * (0.5 + 0.5 * math.sin(now * 70))   # the lid flutters down and back
        if lid >= 1:
            d.rectangle([ex - _HALF, ey - _HALF - 2, ex + _HALF, ey - _HALF + lid], fill=0)
        sgn = -1 if side == 0 else 1                  # stress marks at its outer corner
        bx, by = ex + sgn * 22, ey - 20
        for k in range(3):
            a = math.radians(-90 + sgn * (25 + 30 * k))
            r0, r1 = 2, 2 + 3 * tw + (k == 1)
            d.line([(bx + r0 * math.cos(a), by + r0 * math.sin(a)),
                    (bx + r1 * math.cos(a), by + r1 * math.sin(a))], fill=1)
    sx = round(0.6 * math.sin(now * 41))          # the mug trembles with Pip
    cx, cy = W - 20 + sx, H - 10
    d.rounded_rectangle([cx, cy, cx + 12, cy + 9], radius=2, fill=1)              # cup
    d.arc([cx + 11, cy + 1, cx + 17, cy + 8], start=-80, end=80, fill=1, width=2)  # handle
    slosh = math.sin(now * 9) * 0.8               # the coffee's surface, jiggling inside the rim
    d.line([(cx + 2, cy + 2 + slosh), (cx + 10, cy + 2 - slosh)], fill=0)
    for i in range(2):                            # steam: two curls rising, widening, thinning at the top
        sx = cx + 3 + i * 6
        pts = [(sx + math.sin(f * 5.5 - now * 3.2 + i * 2) * (0.9 + 1.5 * f), cy - 1 - f * 12)
               for f in (j / 9 for j in range(10))]
        d.line(pts[:7], fill=1, joint="curve")
        d.point(pts[7::2], fill=1)


MOOD = Mood("wired", dw=3, dh=3, sway=(0.45, 31), decor=_decor)   # sway = a fine caffeine tremor
