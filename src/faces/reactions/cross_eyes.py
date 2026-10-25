"""Cross-eyed -- derp. The eyes snap in toward the nose and narrow a touch, stopping with a thin gap so
they still read as two eyes crowding together (not one merged blob), hold there, then spring back
apart with a little overshoot. Everything moves in whole-pixel steps, mirrored, so both eyes always
move together -- a fractional shift rounds one eye one way and the other the other, which reads as
one eye twitching on its own."""
import math

from ..primitives import smoothstep
from ..spec import Reaction

_GAP, _EYE = 10, 36            # the engine's resting gap between the eyes / eye width (px)
_TRIM = 3                      # px each eye narrows by on each side while crossed
_MIN_GAP = 2                   # px left between the eyes at the tightest
_IN = (_GAP + 2 * _TRIM - _MIN_GAP) // 2   # px each eye travels in to leave that gap
_SNAP, _RELEASE = 0.18, 0.74   # fraction of the move: the snap in ends / the spring back starts


def _cross(p):
    """How crossed: 0..1 in, held at 1, then springs apart (dipping a touch below 0) and settles."""
    if p < _SNAP:
        return smoothstep(p / _SNAP)
    if p < _RELEASE:
        return 1.0
    q = (p - _RELEASE) / (1 - _RELEASE)
    return math.cos(q * math.pi * 1.5) * (1 - q) ** 1.5


def _motion(p, e):   # snap in, hold, spring back -- whole pixels, mirrored
    c = _cross(p)
    conv = float(round(_IN * c))                                 # whole px: both eyes round the same way
    trim = round(_TRIM * max(0.0, c))                            # narrow by whole px per side
    return 0.0, 0.0, conv, (_EYE - 2 * trim) / _EYE, 1.0


REACTION = Reaction("cross_eyes", dur=1.3, motion=_motion)


if __name__ == "__main__":
    def gap(p):
        _, _, conv, sw, _ = _motion(p, 0)
        return _GAP + _EYE * (1 - sw) - 2 * conv
    gaps = [gap(i / 400) for i in range(401)]
    assert min(gaps) >= _MIN_GAP - 1e-9 and min(gaps) <= _MIN_GAP + 1e-9, "as close as it gets, never touching"
    assert gaps[0] == _GAP and gaps[-1] == _GAP, "start and end apart at rest"
    for i in range(401):
        _, _, conv, sw, _ = _motion(i / 400, 0)
        trim = _EYE * (1 - sw) / 2
        assert conv == int(conv) and abs(trim - round(trim)) < 1e-9, "whole-pixel steps only"
    held = {_motion(p / 100, 0)[2:4] for p in range(20, 74)}
    assert len(held) == 1, "holds perfectly still while crossed"
    print("cross_eyes ok")
