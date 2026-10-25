"""Expectant gaze + three pulsing link dots -- connecting."""
import math

from ..spec import Action


def _pose(now):   # expectant, waiting on the link
    return math.sin(now * 1.5) * 3, math.sin(now * 2.0) * 2, 1.0


def _overlay(d, W, H, now, ox=0.0, oy=0.0):  # three dots pulse in sequence -- "connecting"
    cy = H - 11
    for i in range(3):
        t = (math.sin(now * 4 - i * 1.1) + 1) / 2          # staggered 0..1 pulse
        s = 1.5 + 2.5 * t
        x = W / 2 - 10 + i * 10
        d.ellipse([x - s / 2, cy - s / 2, x + s / 2, cy + s / 2], fill=1)


ACTION = Action("connecting", mood="attentive", pose=_pose, overlay=_overlay)
