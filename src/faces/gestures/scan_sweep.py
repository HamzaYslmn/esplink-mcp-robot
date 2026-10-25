"""One smooth sensor sweep across."""
import math

from ..spec import Gesture


def _motion(p, e):   # one smooth sensor sweep
    return -math.sin(p * math.pi * 2) * 15, 0.0, 0.0, 1.0, 1.0


GESTURE = Gesture("scan_sweep", dur=1.6, motion=_motion)
