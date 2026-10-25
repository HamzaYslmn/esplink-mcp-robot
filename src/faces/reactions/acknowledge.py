"""One crisp dip -- "on it". A single firm drop that squashes at the bottom, then a springy lift that
overshoots a touch above level before it settles."""
from ..primitives import smoothstep
from ..spec import Reaction

_DEPTH, _OVERSHOOT = 13.0, 2.5   # px down at the dip / px above level on the rebound


def _y(p):
    """Head height in px: a fast drop, a springy lift past level, then settle."""
    if p < 0.3:
        return _DEPTH * smoothstep(p / 0.3)
    if p < 0.72:
        return _DEPTH + (-_OVERSHOOT - _DEPTH) * smoothstep((p - 0.3) / 0.42)
    return -_OVERSHOOT * (1 - smoothstep((p - 0.72) / 0.28))


def _motion(p, e):   # one firm dip -- "on it"
    y = _y(p)
    d = max(0.0, y) / _DEPTH                                     # squash only on the way down
    return 0.0, y, 0.0, 1.0 + 0.05 * d, 1.0 - 0.18 * d


REACTION = Reaction("acknowledge", dur=0.6, motion=_motion)


if __name__ == "__main__":
    ys = [_y(i / 100) for i in range(101)]
    assert ys[0] == 0 and abs(ys[-1]) < 1e-9, "starts and ends level"
    assert max(ys) >= _DEPTH - 1e-9 and min(ys) <= -_OVERSHOOT + 1e-9, "a full dip and a springy rebound"
    print("acknowledge ok")
