"""Eyes dart back and forth -- scanning."""
import math

from ..spec import Gesture


def _motion(p, e):   # darting back-and-forth
    return math.sin(p * math.pi * 2) * 16 * e, 0.0, 0.0, 1.0, 1.0


GESTURE = Gesture("scan", dur=1.3, motion=_motion)
