"""Hyperspace -- stars streak outward from the centre as Pip jumps to warp."""
import math

from ..primitives import rand
from ..spec import Vibe

_N = 30             # stars
_CX, _CY = 64, 32   # the vanishing point (screen centre)
_MAXR = 74          # past the far corner -> stars vanish off-edge


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    for i in range(_N):
        ang = rand(i) * 2 * math.pi
        ca, sa = math.cos(ang), math.sin(ang)
        ph = (now * (0.35 + rand(i, 1) * 0.5) + rand(i, 2)) % 1.0
        r = ph * ph * _MAXR                              # accelerate outward
        r0 = max(0.0, r - (3 + 10 * ph))                 # streak lengthens near the edge
        d.line([_CX + ca * r0, _CY + sa * r0, _CX + ca * r, _CY + sa * r], fill=1)


VIBE = Vibe("warp", mood="awe", overlay=_overlay)
