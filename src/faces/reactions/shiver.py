"""Brrr... brrr -- a cold shiver in two bursts: the eyes hunch down and narrow, and shake side to side
at a rate every renderer can show (~5 shakes/s: well under the panel's ~30 fps and the 14 fps
preview, so no frame rate samples it into a standstill)."""
import math

from ..primitives import smoothstep
from ..spec import Reaction

_DUR = 1.1                     # s
_HZ, _AMP = 5.0, 5.0           # shakes per second (<= a third of the slowest 14 fps renderer) / px each way
_BURSTS = ((0.04, 0.46), (0.56, 0.96))   # the two "brrr"s, as fractions of the move


def _burst(p):
    """0..1 how hard it's shivering right now (eased in and out per burst)."""
    for a, b in _BURSTS:
        if a <= p <= b:
            q = (p - a) / (b - a)
            return smoothstep(q / 0.2) * smoothstep((1 - q) / 0.2)
    return 0.0


def _motion(p, e):   # hunch down, narrow, shake in two bursts
    hunch = smoothstep(min(p / 0.1, (1 - p) / 0.1, 1.0))         # tense up for the whole move
    x = _AMP * _burst(p) * math.sin(p * _DUR * _HZ * math.tau + 0.8)   # phase-shifted off frame-aligned zeros
    return x, 2.5 * hunch, 0.0, 1.0, 1.0 - 0.2 * hunch


REACTION = Reaction("shiver", dur=_DUR, motion=_motion)


if __name__ == "__main__":
    xs = [_motion(i / 300, 0)[0] for i in range(301)]
    assert max(xs) > 4 and min(xs) < -4, "a visible shake both ways"
    assert _burst(0.5) == 0 and _burst(0.25) > 0.9 and _burst(0.75) > 0.9, "two bursts with a pause"
    assert _HZ * 2.5 <= 14, "slow enough for the 14 fps preview (and the panel) to show every shake"
    seen = [_motion(f / 14 / _DUR, 0)[0] for f in range(int(14 * _DUR) + 1)]   # sampled like the preview
    assert max(seen) > 3 and min(seen) < -3, "the 14 fps preview catches both sides of the shake"
    print("shiver ok")
