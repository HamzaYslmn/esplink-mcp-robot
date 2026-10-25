"""Ha-ha-ha-ha -- a bouncy chuckle: four hops, each lower, the eyes held as happy squinted slits that
stretch a touch in the air and squash wide on each landing (squash & stretch, never just bigger)."""
from ..spec import Reaction

_HOPS = (10.0, 9.0, 7.0, 5.0)  # px each "ha" lifts
_SLIT = 0.5                    # laughing eyes: squinted to half height


def _hop(p):
    """(height 0..1 of this hop's peak, contact 0..1 how hard it's landing) at progress p."""
    i = min(int(p * len(_HOPS)), len(_HOPS) - 1)
    q = p * len(_HOPS) - i
    air = 4 * q * (1 - q)                                        # a parabola per hop
    return _HOPS[i] * air, max(0.0, 1 - min(q, 1 - q) / 0.12)    # squash right around each landing


def _motion(p, e):   # four bouncy hops with happy squinted eyes
    y, contact = _hop(p)
    slit = 1.0 - (1.0 - _SLIT) * min(1.0, p / 0.08, (1 - p) / 0.08)   # squint in, laugh, open back up
    stretch = y / _HOPS[0] * 0.08 - contact * 0.15               # tall in the air, squashed on landing
    return 0.0, -y, 0.0, 1.0 - 0.6 * stretch, slit * (1.0 + stretch)


REACTION = Reaction("laugh", dur=1.3, motion=_motion)


if __name__ == "__main__":
    ys = [_hop(i / 200)[0] for i in range(201)]
    assert max(ys) >= 9.9 and ys[0] == 0, "full first hop from rest"
    peaks = [max(ys[k * 50:(k + 1) * 50]) for k in range(4)]
    assert all(a > b for a, b in zip(peaks, peaks[1:])), "each ha lower than the last"
    assert _motion(0.5, 0)[4] < 0.75, "eyes squint while laughing"
    print("laugh ok")
