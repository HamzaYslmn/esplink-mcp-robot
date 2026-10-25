"""Glance up as the lids snap shut, then reopen."""
from ..spec import Gesture


def _motion(p, e):
    return 0.0, -7 * e, 0.0, 1.0, 1.0 - 0.9 * e


GESTURE = Gesture("blink_up", dur=0.5, motion=_motion)
