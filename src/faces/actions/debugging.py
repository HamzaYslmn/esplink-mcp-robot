"""Eyes track a beetle skittering along the bottom -- debugging."""
import math

from ..spec import Action


def _pose(now):   # eyes track the bug skittering along the bottom, squinting
    return math.sin(now * 1.4) * 12 + math.sin(now * 3.1) * 3, 5 + math.sin(now * 4.0), 0.9


def _overlay(d, W, H, now, ox=0.0, oy=0.0):  # a beetle skitters along the bottom, legs twitching -- "debugging"
    cx = W / 2 + math.sin(now * 1.4) * (W / 2 - 14)
    cy = H - 8
    face = 1 if math.cos(now * 1.4) >= 0 else -1          # head leads the way it scuttles
    d.ellipse([cx - 6, cy - 4, cx + 6, cy + 4], fill=1)  # shell
    hx = cx + face * 6
    d.ellipse([hx - 2, cy - 2, hx + 2, cy + 2], fill=1)  # head
    d.line([cx, cy - 4, cx, cy + 4], fill=0, width=1)    # wing split
    for k in (-1, 1):                                     # six twitching legs, top & bottom rows
        for j in range(3):
            px = cx - 4 + j * 4
            wig = math.sin(now * 14 + j + (k + 1)) * 1.5
            d.line([px, cy + k * 3, px + wig, cy + k * 6], fill=1, width=1)
    d.line([hx, cy - 1, hx + face * 3, cy - 4], fill=1, width=1)  # antennae
    d.line([hx, cy + 1, hx + face * 3, cy - 2], fill=1, width=1)


ACTION = Action("debugging", mood="suspicious", pose=_pose, overlay=_overlay)
