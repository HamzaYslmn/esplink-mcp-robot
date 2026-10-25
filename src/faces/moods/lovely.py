"""Smitten -- two beating hearts, little hearts drifting up, sparkles twinkling."""
import math

from ..painters import sparkle
from ..spec import Mood


def _heart(d, cx, cy, s):   # smooth parametric heart centred at (cx, cy), ~s px wide
    sc = s / 33.0
    pts = [(cx + 16 * math.sin(t) ** 3 * sc,
            cy - (13 * math.cos(t) - 5 * math.cos(2 * t)
                  - 2 * math.cos(3 * t) - math.cos(4 * t)) * sc + 2 * sc)
           for t in (i * math.pi / 36 for i in range(72))]
    d.polygon(pts, fill=1)


def _beat(now):   # lub-dub: two quick thumps then a rest, ~1 beat/sec
    p = (now * 1.1) % 1.0
    return math.exp(-(p * 7) ** 2) + 0.55 * math.exp(-((p - 0.24) * 7) ** 2)


def _decor(d, W, H, now, ox=0.0, oy=0.0):
    s = 30 * (1 + 0.16 * _beat(now))                       # the pair beats together
    for cx in (W * 0.32, W * 0.68):
        _heart(d, cx + ox, H * 0.5 + oy, s)
    for i in range(2):                                     # a couple of hearts drifting up, looping
        t = (now * 0.3 + i * 0.5) % 1.0
        fx = (0.12, 0.88)[i] + 0.03 * math.sin(now * 2 + i)
        _heart(d, fx * W, H * (1.0 - t) - 2, 4 + 2 * (1 - t))
    for i in range(2):                                     # a sparkle on each side, twinkling
        fx, fy = ((0.07, 0.22), (0.93, 0.24))[i]
        sparkle(d, fx * W, fy * H, 1.5 + 2 * abs(math.sin(now * 3 + i * 1.6)))


MOOD = Mood("lovely", bare=True, decor=_decor)
