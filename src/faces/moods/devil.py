"""Devil -- a sharp glare with slit pupils under curved horns, embers drifting up past them.
Eyes only (Pip has no mouth): slightly smaller eyes, like cat, leave room for the horns, which ride
the gaze."""
from ..painters import glare
from ..primitives import rand
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # wicked glare + a tall slit pupil, nudged toward the nose
    glare(d, x, y, w, h, 0.6, ir)
    cx = x + w * (0.44 if ir else 0.56)                             # pupils lean inward: the stare closes in
    top, bot = y + h * 0.44, y + h * 0.9                            # starts below the brow cut, so it never joins it
    half = max(2.0, w * 0.08)
    d.polygon([(cx, top), (cx + half, (top + bot) / 2), (cx, bot), (cx - half, (top + bot) / 2)], fill=0)


def _horn(d, ox, oy, side, W):
    """One crescent horn above an eye's outer corner, curling outward. side -1 left / +1 right."""
    cx = W / 2 + side * 31 + ox                                    # over the eye's outer half
    pts = [(-8, 15), (-12, 10), (-12, 4), (-8, 0),                  # thick base flares out, tip hooks back up
           (-6, 5), (-5, 9), (2, 15)]                               # inner edge back down to the base
    d.polygon([(cx + side * -px, py + oy) for px, py in pts], fill=1)


def _embers(d, W, now, ox, oy):
    """A few sparks rising past the horns, each on its own loop, flickering as they climb."""
    for i in range(4):
        side = -1 if i % 2 else 1
        u = (now * 0.35 + rand(i)) % 1.0                            # 0 -> 1 as it rises
        x = W / 2 + side * (44 + 6 * rand(i, 1)) + 2 * (rand(i, int(now * 6)) - 0.5) + ox
        y = 16 - u * 17 + oy
        if rand(i, int(now * 10)) > 0.25:                           # flicker
            d.point([(x, y)], fill=1)
            if u < 0.4:
                d.point([(x, y + 1)], fill=1)                       # fresh sparks are a touch bigger


def _decor(d, W, H, now, ox=0.0, oy=0.0):
    _horn(d, ox, oy, -1, W)
    _horn(d, ox, oy, 1, W)
    _embers(d, W, now, ox, oy)


MOOD = Mood("devil", dw=-4, dh=-8, paint=_paint, decor=_decor)   # smaller eyes -> room for the horns
