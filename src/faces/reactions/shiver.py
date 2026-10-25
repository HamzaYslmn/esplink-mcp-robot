"""A fast, tight tremble."""
import math

from ..spec import Reaction


def _motion(p, e):
    return math.sin(p * math.pi * 16) * 3 * e, math.cos(p * math.pi * 22) * 2 * e, 0.0, 1.0, 1.0


REACTION = Reaction("shiver", dur=0.7, motion=_motion)
