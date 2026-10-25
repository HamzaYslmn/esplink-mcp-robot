"""Shakes settling -- no."""
import math

from ..spec import Reaction


def _motion(p, e):   # shakes settling -- no
    return math.sin(p * math.pi * 6) * 9 * e * (1.0 - 0.45 * p), 0.0, 0.0, 1.0, 1.0


REACTION = Reaction("refuse", dur=1.2, motion=_motion)
