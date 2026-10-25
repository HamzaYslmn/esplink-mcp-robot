"""Both eyes converge toward the nose."""
from ..spec import Reaction


def _motion(p, e):
    return 0.0, 0.0, 9.0 * e, 1.0, 1.0


REACTION = Reaction("cross_eyes", dur=0.9, motion=_motion)
