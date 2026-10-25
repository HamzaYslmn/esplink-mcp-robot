"""Shakes -- no. A clean head shake: four quick swings left-right-left-right, tapering off, snapping
between sides and settling back to centre. Both eyes keep their size; only the head moves."""
from ..primitives import smoothstep
from ..spec import Reaction

_KEYS = ((0.0, 0.0), (0.13, -16.0), (0.33, 16.0), (0.53, -12.0), (0.71, 7.0), (0.86, -2.0), (1.0, 0.0))   # (p, x px)


def _x(p):
    """Head turn in px: snap between keyframes (smoothstep), so each swing lands firmly."""
    for (p0, x0), (p1, x1) in zip(_KEYS, _KEYS[1:]):
        if p0 <= p <= p1:
            return x0 + (x1 - x0) * smoothstep((p - p0) / (p1 - p0))
    return 0.0


def _motion(p, e):   # left-right-left-right, tapering, then centre
    return _x(p), 0.0, 0.0, 1.0, 1.0


REACTION = Reaction("refuse", dur=1.1, motion=_motion)


if __name__ == "__main__":
    xs = [_x(i / 100) for i in range(101)]
    assert xs[0] == 0 and xs[-1] == 0, "starts and ends centred"
    assert min(xs) <= -15.9 and max(xs) >= 15.9, "full swings both ways"
    sides = [x for _, x in _KEYS[1:-1]]
    assert all(a * b < 0 for a, b in zip(sides, sides[1:])), "alternates left and right"
    assert all(abs(a) >= abs(b) for a, b in zip(sides, sides[1:])), "tapers off"
    assert _motion(0.3, 0.0)[3:] == (1.0, 1.0), "eyes keep their size"
    print("refuse ok")
