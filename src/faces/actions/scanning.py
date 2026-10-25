"""Scanning -- the eyes sweep the room like a scanner: narrowed to a slit, they pan at a steady,
mechanical speed along one line, pause at its edge, hop crisply to the next line and pan again.
Each pass picks a route -- raster rows, serpentine, columns, or a ring round the edge -- and
up to two events that interrupt a pan part-way:
  * spot    -- something catches the eye: the pan halts, eyes pop wide and hold, then carry on;
  * rescan  -- not sure: the pan backs up over the last stretch, squinting, and sweeps it again;
  * lock-on -- the eyes freeze, open wide, then slowly squeeze down to focus;
  * startle -- a sudden wide-eyed glance off to a far corner, then straight back to the line;
  * lost    -- the gaze drifts off in a slow wander, then picks the pan back up.
A pass ends on a centred look-around, maybe with a blink or a double blink.
Stateless: every pass is hashed off the clock."""
import math
from functools import lru_cache

from ..primitives import rand, smoothstep
from ..spec import Action

_X, _Y = 15.0, 7.0                                # gaze reach, px
_PASS, _REST = 12.0, 1.0                          # s per pass slot, s it keeps for the closing rest at least
_PAN = (1.3, 2.6)                                # s per pan line, min/max (slower when the pass is quiet)
_HOP, _EDGE = 0.35, 0.3                           # s settling at a line's start, s pausing at its end
_KICK, _OVER = 0.1, 0.25                          # s a hop overshoots for, fraction of the hop it overshoots
_EVENTS = {"spot": 0.7, "rescan": 1.2, "lock": 1.2, "startle": 0.85, "lost": 1.4}   # s each one costs
_LOOK = {"pan": 0.66, "hop": 0.85, "edge": 0.85, "spot": 1.15, "rescan": 0.55, "startle": 1.25,
         "lost": 0.95, "rest": 1.0}               # eye height per beat


def _route(p):
    """The pass's pan lines [(from, to)]."""
    rows, style = (-_Y, 0.0, _Y), int(rand(p, 0) * 4)
    if style == 1:                                # serpentine
        lines = [((-_X, y), (_X, y))[::(-1) ** r] for r, y in enumerate(rows)]
    elif style == 2:                              # columns, top to bottom
        lines = [((x, -_Y), (x, _Y)) for x in (-_X, 0.0, _X)]
    elif style == 3:                              # ring round the edge
        c = ((-_X, -_Y), (_X, -_Y), (_X, _Y), (-_X, _Y))
        lines = list(zip(c, c[1:] + c[:1]))
    else:                                         # raster
        lines = [((-_X, y), (_X, y)) for y in rows]
    if rand(p, 7) < 0.5:                          # sometimes run it mirrored
        lines = [((-a[0], a[1]), (-b[0], b[1])) for a, b in lines]
    return lines


@lru_cache(maxsize=8)
def _plan(p):
    """[(start s, kind, from, to, dur s)] for pass p, ending on a rest that fills the slot."""
    lines = _route(p)
    n = int(rand(p, 1) * 10)
    n = 0 if n < 2 else 1 if n < 7 else 2         # 20% quiet, 50% one event, 30% two
    events = {}                                   # line -> (fraction along it, event)
    for i in range(n):
        events[int(rand(p, 10 + i) * len(lines))] = (0.3 + rand(p, 20 + i) * 0.4,
                                                      tuple(_EVENTS)[int(rand(p, 30 + i) * len(_EVENTS))])
    spare = _PASS - _REST - len(lines) * (_HOP + _EDGE) - sum(_EVENTS[e] for _, e in events.values())
    pan = min(_PAN[1], max(_PAN[0], spare / len(lines)))
    beats, pos = [], (0.0, 0.0)

    def go(kind, to, dur, frm=None):
        nonlocal pos
        beats.append((kind, frm or pos, to, dur))
        pos = to

    for i, (a, b) in enumerate(lines):
        go("hop", a, _HOP)
        if i in events:
            f, e = events[i]
            q = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            go("pan", q, pan * f)
            if e == "rescan":                     # back up over the last stretch, then sweep it again
                r = (a[0] + (b[0] - a[0]) * f * 0.5, a[1] + (b[1] - a[1]) * f * 0.5)
                go("rescan", r, 0.6)
                go("rescan", q, 0.6)
            elif e == "startle":                  # what was THAT -- a far corner, then back
                go("startle", ((22.0, -22.0)[rand(p, 50) < 0.5], (9.0, -9.0)[rand(p, 51) < 0.5]), 0.5)
                go("hop", q, 0.35)
            else:
                go(e, q, _EVENTS[e])
            go("pan", b, pan * (1 - f))
        else:
            go("pan", b, pan)
        go("edge", b, _EDGE)
    out, t = [], 0.0
    for kind, frm, to, d in beats:
        out.append((t, kind, frm, to, d))
        t += d
    out.append((t, "rest", pos, (0.0, 0.0), _PASS - t))
    return tuple(out)


def _pose(now):
    p, t = int(now / _PASS), now % _PASS
    plan = _plan(p)
    start, kind, (fx, fy), (gx, gy), dur = next(b for b in reversed(plan) if b[0] <= t)
    s = t - start
    if kind in ("pan", "rescan"):                 # a steady, mechanical sweep: constant speed
        u = min(1.0, s / dur)
        return fx + (gx - fx) * u, fy + (gy - fy) * u, _LOOK[kind]
    if kind == "lock":                            # freeze, open wide, squeeze down to focus
        return gx, gy, 1.2 - 0.6 * smoothstep(s / dur)
    if kind == "lost":                            # a slow wander off the line
        return gx + math.sin(s * 1.3) * 7, gy + math.sin(s * 0.9) * 4, _LOOK[kind]
    if kind == "rest":                            # centred look-around, maybe a blink or two
        b = rand(p, 9)
        if (b < 0.6 and 0.25 < s < 0.4) or (b < 0.25 and 0.55 < s < 0.7):
            return 0.0, 0.0, 0.12
        return math.sin(s * 0.9) * 4, math.sin(s * 0.6) * 2, _LOOK[kind]
    if s < _KICK and kind in ("hop", "startle"):  # overshoot the hop, the ease settles it back
        gx, gy = gx + (gx - fx) * _OVER, gy + (gy - fy) * _OVER
    return gx, gy, _LOOK[kind]


ACTION = Action("scanning", mood="attentive", pose=_pose)


if __name__ == "__main__":                        # ponytail check: every pass fits its slot and ends on a long-enough rest
    for p in range(500):
        plan = _plan(p)
        assert all(a[0] <= b[0] for a, b in zip(plan, plan[1:])), p
        assert plan[-1][1] == "rest" and plan[-1][4] >= _REST - 1e-9, (p, plan[-1])
        for i in range(int(_PASS * 50)):
            _pose(p * _PASS + i / 50)
    print("ok")
