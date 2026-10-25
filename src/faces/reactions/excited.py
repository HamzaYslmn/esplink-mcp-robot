"""Eager bounce -- a quick crouch to wind up, a big jump, then fast rebound hops. Squash & stretch:
tall and thin in the air, short and wide on landing -- never just bigger."""
from ..primitives import smoothstep
from ..spec import Reaction

_CROUCH = 0.14                 # fraction of the move spent winding up
_HOPS = (12.0, 7.0, 4.0)       # px each jump lifts after the crouch


def _jump(p):
    """(height px, squash -1..1: + stretched tall, - squashed wide) at progress p."""
    if p < _CROUCH:                                              # anticipation: dip and squash
        c = smoothstep(p / _CROUCH)
        return -2.5 * c, -0.6 * c
    q = (p - _CROUCH) / (1 - _CROUCH) * len(_HOPS)
    i = min(int(q), len(_HOPS) - 1)
    f = q - i
    air = 4 * f * (1 - f)
    landing = max(0.0, 1 - min(f, 1 - f) / 0.12)
    return _HOPS[i] * air, air * 0.6 * _HOPS[i] / _HOPS[0] - landing * 0.5 * _HOPS[i] / _HOPS[0]


def _motion(p, e):   # crouch, big jump, quick rebounds
    y, s = _jump(p)
    return 0.0, -y, 0.0, 1.0 - 0.12 * s, 1.0 + 0.15 * s


REACTION = Reaction("excited", dur=1.0, motion=_motion)


if __name__ == "__main__":
    ys = [_jump(i / 200)[0] for i in range(201)]
    assert min(ys) < 0 and max(ys) >= 11.9, "crouches first, then jumps high"
    assert abs(ys[-1]) < 1e-6, "lands back at rest"
    areas = [(1 - 0.12 * s) * (1 + 0.15 * s) for _, s in (_jump(i / 200) for i in range(201))]
    assert all(0.9 < a < 1.05 for a in areas), "squash and stretch keep the eyes' size, not grow them"
    print("excited ok")
