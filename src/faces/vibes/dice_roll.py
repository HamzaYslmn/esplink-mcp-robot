"""A d20 -- rolls once: the hex die tumbles for a beat, settles on a number it holds for five
seconds, then hands the face back to normal. Each fire rolls a fresh number. The eyes shrink and glance up at the die."""
import math

from PIL import ImageFont

from ..primitives import rand
from ..spec import Vibe

_ROLL = 1.4                         # s of tumbling before it settles
_SHOW = 5.0                         # s holding the result
_DONE = _ROLL + _SHOW

try:
    _F = ImageFont.load_default(size=11)
except TypeError:                   # ancient Pillow
    _F = ImageFont.load_default()

def _pose(now):
    return 0.0, 9.0, 0.55           # small eyes, low, looking up at the die


def _hexagon(d, cx, cy, r):
    pts = [(cx + r * math.cos(math.pi / 6 + k * math.pi / 3),
            cy + r * math.sin(math.pi / 6 + k * math.pi / 3)) for k in range(6)]
    d.polygon(pts, outline=1)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    t = now.t
    cx, cy = W // 2, 12
    if t < _ROLL:                                          # tumbling: number + position flicker
        n = 1 + int(rand(int(now * 18)) * 20)
        jx = (rand(int(now * 18), 1) - 0.5) * 3
        jy = (rand(int(now * 18), 2) - 0.5) * 3
    else:                                                  # settled, held for _SHOW
        n = 1 + int(rand(now.seed) * 20)                 # rolled once per play
        jx = jy = 0.0
    _hexagon(d, cx + jx, cy + jy, 10)
    s = str(n)
    d.text((cx + jx - d.textlength(s, font=_F) / 2, cy + jy - 6), s, font=_F, fill=1)


def _expired(now):
    return now.t >= _DONE                          # roll + show done -> back to natural


VIBE = Vibe("dice_roll", mood="neutral", pose=_pose, overlay=_overlay, expired=_expired, still=True)
