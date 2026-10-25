"""A wary squint -- the eyes snap to a tight slit, hold it with a slow suspicious glance to one side
and back, then ease open."""
import math

from ..primitives import smoothstep
from ..spec import Reaction

_SLIT = 0.25                   # eye height at the tightest
_SNAP, _OPEN = 0.12, 0.78      # fraction of the move: the snap shut ends / the easing open starts


def _lid(p):
    """0..1 how squinted: snaps in fast, holds, eases out slow."""
    if p < _SNAP:
        return smoothstep(p / _SNAP)
    if p < _OPEN:
        return 1.0
    return 1 - smoothstep((p - _OPEN) / (1 - _OPEN))


def _motion(p, e):   # snap to a slit, side-eye, ease open
    lid = _lid(p)
    glance = math.sin(math.pi * min(1.0, max(0.0, (p - _SNAP) / (_OPEN - _SNAP)))) * 7   # slow look aside and back
    return glance, 0.0, 0.0, 1.0, 1.0 - (1.0 - _SLIT) * lid


REACTION = Reaction("squint", dur=1.4, motion=_motion)


if __name__ == "__main__":
    hs = [_motion(i / 200, 0)[4] for i in range(201)]
    assert min(hs) <= _SLIT + 1e-9 and hs[0] == 1 and abs(hs[-1] - 1) < 1e-9, "snaps to a slit, opens back fully"
    assert _lid(_SNAP) == 1 and _lid(0.05) > 0.3, "the squint lands fast"
    assert max(_motion(i / 200, 0)[0] for i in range(201)) > 6.5, "a visible sideways glance"
    print("squint ok")
