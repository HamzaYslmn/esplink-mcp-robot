"""Deep snore -- eyes flat shut while the whole face slowly heaves with each breath and a big 'Z'
swells out on every exhale. The breathing rhythm is what sets it apart from `sleepy`'s idle doze.
(Wears `neutral`, not `sleepy`: sleepy carries its own decor-Z that would double up with these.)"""
import math

from PIL import ImageFont

from ..spec import Vibe

_BREATH = 2.6                       # one inhale+snore cycle (s) -- slow, heavy sleep


def _font(sz):
    try:
        return ImageFont.load_default(size=sz)
    except TypeError:               # ancient Pillow
        return ImageFont.load_default()


_FZ = [_font(8), _font(11), _font(15)]


def _pose(now):
    heave = math.sin(now / _BREATH * 2 * math.pi)   # chest rises on inhale, sinks on exhale
    return 0.0, 6.0 + heave * 2.0, 1 / 36           # 1px lids, a touch low, gently heaving


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    b = (now / _BREATH) % 1.0
    if b < 0.45:                                    # inhale -- quiet, nothing puffs out yet
        return
    e = (b - 0.45) / 0.55                           # 0..1 snore/exhale progress
    for k in range(2):                              # a little burst of Z's pushed out on the snore
        ek = e - k * 0.3
        if 0.0 <= ek < 0.9:
            fi = min(2, int(ek * 3))                # the Z swells small -> big as it drifts up
            d.text((W * 0.58 + ek * 12 + k * 4 + ox, H * 0.5 - ek * 26), "Z", font=_FZ[fi], fill=1)


VIBE = Vibe("snore", mood="neutral", pose=_pose, overlay=_overlay, still=True)
