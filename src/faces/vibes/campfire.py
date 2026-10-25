"""Campfire -- one big fire: a tall central flame flanked by smaller tongues, each flickering on
its own; embers rise, accelerate and sway as they cool, and the odd spark pops off the crown. Pip
watches it, focused, gazing down."""
import math

from ..primitives import rand
from ..spec import Vibe

_TONGUES = (    # (x-offset from centre, half-width, max height, seed) -- different spikes
    (-13, 5, 14, 0),
    (-7, 7, 24, 1),
    (0, 9, 36, 2),          # the tall central spike
    (6, 7, 26, 3),
    (13, 5, 16, 4),
)


def _pose(now):
    return 0.0, 5.0, 1.0          # eyes full-open, gazing down into the fire -- focused, not bored


def _tongue(d, cx, base, w, h, sway):
    tip = cx + sway                                            # the tip leans with the draught
    d.polygon([(cx - w, base), (cx + w, base), (tip + 1, base - h), (tip - 2, base - h * 0.7)], fill=1)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    cx, base = W // 2, H - 1
    t = int(now * 14)                                         # flicker tick
    for dx, w, hmax, seed in _TONGUES:
        h = hmax * (0.55 + 0.45 * rand(seed, t))             # each tongue's height jitters on its own
        sway = (rand(seed, t + 7) - 0.5) * 6
        _tongue(d, cx + dx, base, w, h, sway)
    for k in range(8):                                        # embers: rise, accelerate, sway, vary in size
        life = (now * (0.5 + 0.4 * rand(k, 3)) + rand(k, 9)) % 1.0
        ex = cx + (rand(k, 1) - 0.5) * 30 + math.sin(now * 2 + k) * life * 7   # turbulence widens as it rises
        ey = base - 8 - (life ** 0.8) * (H - 8)              # buoyancy fades near the top
        if rand(k, 5) > 0.5:
            d.point((ex, ey), fill=1)
        else:
            d.rectangle([ex, ey, ex + 1, ey + 1], fill=1)    # a fatter, slower ember
    if rand(t) > 0.82:                                        # a spark popping off the crown
        d.point((cx + (rand(t, 2) - 0.5) * 18, base - 32 - rand(t, 4) * 8), fill=1)


VIBE = Vibe("campfire", mood="focused", pose=_pose, overlay=_overlay)
