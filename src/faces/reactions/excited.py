"""Eager bounce -- the eyes hop and swell."""
import math

from ..spec import Reaction


def _motion(p, e):
    return 0.0, -abs(math.sin(p * math.pi * 5)) * 8 * e, 0.0, 1.0 + 0.22 * e, 1.0 + 0.22 * e


REACTION = Reaction("excited", dur=0.9, motion=_motion)
