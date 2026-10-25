"""One crisp dip -- "on it"."""
from ..spec import Reaction


def _motion(p, e):   # one crisp dip -- "on it"
    return 0.0, e * 8, 0.0, 1.0, 1.0


REACTION = Reaction("acknowledge", dur=0.45, motion=_motion)
