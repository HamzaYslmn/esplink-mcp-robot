"""An eye-roll -- ugh. One slow, fluid loop with the eyes wide open: out left, up over the top --
lingering there a beat -- and down the right side back home."""
import math

from ..spec import Reaction

_RX, _RY = 14.0, 7.0           # px: the loop's half-width / half-height (it peaks 2*_RY above home)
_DWELL = 0.3                   # how much the roll slows at the top (0 = even speed)


def _ease(k):
    """Smootherstep: starts and ends at rest with no jerk, so the loop glides."""
    k = max(0.0, min(1.0, k))
    return k * k * k * (k * (6 * k - 15) + 10)


def _loop(s):
    """A circle hung above home: s=0 home, .25 left, .5 the top, .75 right, 1 home again."""
    a = math.tau * s
    return -_RX * math.sin(a), -_RY * (1 - math.cos(a))


def _motion(p, e):   # one slow loop over the top, lingering at the peak
    k = _ease(p)
    x, y = _loop(k + _DWELL / math.tau * math.sin(math.tau * k))   # slows near the top, still always forward
    return x, y, 0.0, 1.0, 1.0


REACTION = Reaction("roll", dur=1.8, motion=_motion)


if __name__ == "__main__":
    pts = [_motion(i / 600, 0) for i in range(601)]
    xs, ys = [m[0] for m in pts], [m[1] for m in pts]
    assert abs(min(ys) + 2 * _RY) < 0.05, "rolls right up over the top"
    assert min(xs) < -13.9 and max(xs) > 13.9, "swings fully out both sides"
    steps = [math.hypot(xs[i + 1] - xs[i], ys[i + 1] - ys[i]) for i in range(600)]
    assert max(steps) < 3 * sum(steps) / len(steps), "glides: no sudden jumps along the loop"
    assert sum(y < -2 * _RY * 0.9 for y in ys) > 600 * 0.12, "lingers at the top"
    assert all(m[3:] == (1.0, 1.0) for m in pts), "eyes stay fully open -- a roll, not a squint"
    assert pts[0][:2] == (0.0, 0.0) and abs(xs[-1]) < 1e-9, "home at both ends"
    print("roll ok")
