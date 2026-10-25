"""Eyes pop wide -- a startle: a tiny squint, then the eyes snap wide with a jolt up, and wobble
elastically back to normal."""
import math

from ..primitives import smoothstep
from ..spec import Reaction

_WIND, _SNAP = 0.12, 0.22      # fraction of the move: the squint wind-up / the snap to full size
_WIDE = 1.38                   # peak size


def _size(p):
    """Eye scale at progress p: squint, snap wide, then a damped elastic wobble back to 1."""
    if p < _WIND:
        return 1.0 - 0.15 * smoothstep(p / _WIND)
    if p < _SNAP:
        return 0.85 + (_WIDE - 0.85) * smoothstep((p - _WIND) / (_SNAP - _WIND))
    q = (p - _SNAP) / (1 - _SNAP)
    return 1.0 + (_WIDE - 1.0) * math.exp(-4.5 * q) * math.cos(q * math.pi * 3)


def _motion(p, e):   # squint, pop wide with a jolt up, wobble back
    s = _size(p)
    jolt = -4 * max(0.0, (s - 1) / (_WIDE - 1))                  # the head jerks up as the eyes pop
    return 0.0, jolt, 0.0, s, s


REACTION = Reaction("pop", dur=0.7, motion=_motion)


if __name__ == "__main__":
    ss = [_size(i / 200) for i in range(201)]
    assert min(ss[:30]) < 0.9 and max(ss) >= _WIDE - 1e-6, "squints, then pops fully wide"
    assert abs(ss[-1] - 1) < 0.05, "settles back to normal size"
    assert min(ss[60:]) < 1.0, "an elastic wobble past normal on the way back"
    print("pop ok")
