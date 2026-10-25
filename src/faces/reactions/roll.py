"""Eyes roll in a full circle."""
import math

from ..spec import Reaction


def _motion(p, e):
    return math.cos(p * math.pi * 2) * 11 * e, math.sin(p * math.pi * 2) * 7 * e, 0.0, 1.0, 1.0


REACTION = Reaction("roll", dur=0.9, motion=_motion)
