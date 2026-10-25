"""Notifications -- app-badge style: Pip's face is the icon, the unread count rides in a hexagon
badge top-right. Each new one fires a hex pulse, a glance up, and a cheeky wink toward it -- the
wink reuses the real `wink_right` gesture via the action's `tic`, so it shares the engine's move
layer with the auto-blink and the two never clash. Count from $PIP_NOTIF; 0 -> a calm, plain face."""
import math
import os

from PIL import ImageFont

from ..spec import Widget

try:
    _F = ImageFont.load_default(size=10)
except TypeError:                       # ancient Pillow
    _F = ImageFont.load_default()

_BX, _BY, _R = 115, 11, 10   # hex badge centre + radius, top-right corner
_DING = 1.4                  # s between "new message" beats (pulse + wink)


def _count():
    try:
        return max(0, int(os.getenv("PIP_NOTIF", "3")))
    except ValueError:
        return 0


def _hex(cx, cy, r):         # flat-top hexagon -> a techy, faceted badge that stays crisp small
    return [(cx + r * math.cos(k * math.pi / 3), cy + r * math.sin(k * math.pi / 3)) for k in range(6)]


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    n = _count()
    if not n:
        return                                                  # nothing unread -> plain face
    ph = (now % _DING) / _DING
    if ph < 0.6:                                                # a hex pulse radiates on each beat
        d.polygon(_hex(_BX, _BY, _R + ph / 0.6 * 17), outline=1)
    r = _R * (1.0 + 0.22 * max(0.0, 1 - ph / 0.18))             # badge pops on arrival, then settles
    d.polygon(_hex(_BX, _BY, r), fill=1)
    d.polygon(_hex(_BX, _BY, r), outline=0)                     # dark rim, sets it off the eye
    txt = str(n) if n < 100 else "99+"
    d.text((_BX - d.textlength(txt, font=_F) / 2, _BY - 6), txt, font=_F, fill=0)


def _pose(now):
    """A gentle glance up toward the badge; the wink itself is the `tic` gesture below."""
    if not _count():
        return 0.0, 0.0, 1.0
    look = max(0.0, 1 - (now % _DING) / _DING / 0.5)
    return 4.0 * look, -2.0 * look, 1.0


WIDGET = Widget("notif_badge", mood="neutral", pose=_pose, overlay=_overlay,
                tic=(lambda now: "wink_right" if _count() else None, _DING))   # wink the near eye each beat
