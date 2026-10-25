"""Eyes pop wide for a beat."""
from ..spec import Reaction


def _motion(p, e):
    return 0.0, 0.0, 0.0, 1.0 + 0.35 * e, 1.0 + 0.35 * e


REACTION = Reaction("pop", dur=0.5, motion=_motion)
