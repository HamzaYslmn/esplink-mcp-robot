"""Nods settling -- yes."""
import math

from ..spec import Reaction


def _motion(p, e):   # nods settling -- yes
    return 0.0, math.sin(p * math.pi * 4) * 7 * e * (1.0 - 0.42 * p), 0.0, 1.0, 1.0


REACTION = Reaction("nod", dur=1.4, motion=_motion)
