"""Two nods -- yes. Each drops fast and lifts back slower, the second smaller; the eyes squash a
touch at the bottom of each dip so it lands with weight."""
from ..primitives import smoothstep
from ..spec import Reaction

_NODS = ((0.0, 0.48, 16.0), (0.48, 0.92, 10.0))  # (start, end, depth px) as fractions of the move


def _dip(p):
    """0..1 how far down the head is: a quick drop, a slower lift, per nod."""
    for a, b, depth in _NODS:
        if a <= p < b:
            q = (p - a) / (b - a)
            down = smoothstep(q / 0.35) if q < 0.35 else 1 - smoothstep((q - 0.35) / 0.65)
            return down * depth / _NODS[0][2]
    return 0.0


def _motion(p, e):   # quick drop, slower lift, twice -- the second smaller
    d = _dip(p)
    return 0.0, _NODS[0][2] * d, 0.0, 1.0 + 0.05 * d, 1.0 - 0.18 * d


REACTION = Reaction("nod", dur=1.2, motion=_motion)


if __name__ == "__main__":
    ds = [_dip(i / 100) for i in range(101)]
    assert ds[0] == 0 and ds[-1] == 0 and max(ds) > 0.98, "starts and ends level, dips the full depth"
    first, second = max(ds[:48]), max(ds[48:])
    assert second < first, "the second nod is the smaller"
    print("nod ok")
