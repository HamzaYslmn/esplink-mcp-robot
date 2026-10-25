"""Cat -- almond slit-pupil eyes, twitching ears, shimmering whiskers and a tiny :3 nose+mouth.
Self-contained: `paint` carves the cat eyes, `decor` draws and animates the rest off `now`."""
import math

from ..painters import brow
from ..primitives import rand
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # almond cat eye -- a slanted top lid, a vertical slit pupil, a glint
    brow(d, x, y, w, h, 0.14, 0.0, ir)                             # top slants gently up-and-out (almond, not a glare)
    cx = x + w / 2
    top, bot = y + h * 0.24, y + h * 0.9
    midy, half = (top + bot) / 2, max(2.0, w * 0.105)
    d.polygon([(cx, top), (cx + half, midy), (cx, bot), (cx - half, midy)], fill=0)   # tall slit pupil
    g = top + (bot - top) * 0.36
    d.ellipse([cx - 2, g - 2, cx + 2, g + 2], fill=1)                                  # bright catchlight


def _flick(now, seed):
    """A quick ear twitch: 0 at rest, a brief 0->1->0 burst every ~4s, staggered per ear by seed."""
    p = (now / 4.0 + rand(seed)) % 1.0
    return math.sin(p / 0.09 * math.pi) if p < 0.09 else 0.0       # lives in the first ~9% of the cycle


def _ear(d, a, b, tip, now, side):
    """One slim cat ear drawn as an open V -- two 2px strokes meeting at a soft tip, base left open
    (no bottom line). `side` (-1 left / +1 right) sets both the twitch stagger and the outward flick."""
    flick = _flick(now, side)
    tx, ty = tip[0] + flick * 3 * side, tip[1] - flick * 1.5
    d.line([a, (tx, ty), b], fill=1, width=2, joint="curve")       # open V, soft tip


def _decor(d, W, H, now, ox=0.0, oy=0.0):  # ears/whiskers/nose ride the gaze; sized to clear the (smaller) eyes
    # -- ears: a slim open V lifted just above each eye, each twitching on its own stagger
    _ear(d, (28 + ox, 15 + oy), (45 + ox, 12 + oy), (35 + ox, 1 + oy), now, -1)              # left
    _ear(d, (W - 28 + ox, 15 + oy), (W - 45 + ox, 12 + oy), (W - 35 + ox, 1 + oy), now, 1)   # right
    # -- whiskers: three a side in the wide cheek margins, tips shimmering
    for i, dy in enumerate((-6, 0, 6)):
        wob = math.sin(now * 2.0 + i) * 1.2
        d.line([(25 + ox, 40 + oy), (3 + ox, 36 + dy + oy + wob)], fill=1)
        d.line([(W - 25 + ox, 40 + oy), (W - 3 + ox, 36 + dy + oy + wob)], fill=1)
    # -- nose + a soft :3 mouth, in the gap just below the eyes
    nx, ny = W / 2 + ox, 47 + oy
    d.polygon([(nx - 3, ny - 1), (nx + 3, ny - 1), (nx, ny + 2)], fill=1)              # nose
    d.arc([nx - 6, ny + 1, nx, ny + 6], 0, 180, fill=1)                                # left lip
    d.arc([nx, ny + 1, nx + 6, ny + 6], 0, 180, fill=1)                                # right lip


MOOD = Mood("cat", dw=-6, dh=-8, paint=_paint, decor=_decor)   # smaller eyes -> room for ears, no overlap
