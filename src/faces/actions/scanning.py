"""Scanning -- a fast, twitchy scanner: eyes narrowed to a slit tick along a line in quick discrete
steps (each one snaps a hair past and settles), blip at its edge, hop to the next line and tick on.
Each pass picks a route -- raster rows, serpentine, columns, or a ring round the edge -- repeated
to fill the slot, and up to two events that interrupt a line part-way:
  * error   -- the read fails: the eyes glitch and flicker, snap back to the line's start, scan it again;
  * rescan  -- not sure: tick back over the last stretch, squinting, then forward again;
  * spot    -- something catches the eye: halt, eyes pop wide and hold, then carry on;
  * lock-on -- freeze, open wide, then squeeze down to focus;
  * startle -- a sudden wide-eyed glance off to a far corner, then straight back to the line;
  * glance  -- distracted: three quick darting looks around, then back to work;
  * ping    -- a line done: a quick double blink, scan complete.
A pass ends on a centred beat: a couple of short looks, maybe a blink.
Stateless: every pass is hashed off the clock."""
from functools import lru_cache

from ..primitives import rand, smoothstep
from ..spec import Action

_X, _Y = 15.0, 7.0                                # gaze reach, px
_PASS, _REST = 8.0, 0.8                           # s per pass slot, s it keeps for the closing rest at least
_PAN, _TICK = 0.7, 0.12                           # s per line, s per scanner step
_HOP, _EDGE = 0.2, 0.15                           # s settling at a line's start, s blipping at its end
_KICK, _OVER = 0.04, 0.3                          # s a step/hop overshoots for, fraction of it overshot
_EVENTS = {"error": 1.2, "rescan": 0.5, "spot": 0.5, "lock": 0.8, "startle": 0.55, "glance": 0.7,
           "ping": 0.4}                           # s each one costs (budget)
_LOOK = {"pan": 0.6, "hop": 0.8, "edge": 0.8, "rescan": 0.5, "spot": 1.15, "startle": 1.25,
         "glance": 1.0, "rest": 1.0}              # eye height per beat


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


def _lerp(a, b, f):
    return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f


@lru_cache(maxsize=8)
def _plan(p):
    """[(start s, kind, from, to, dur s)] for pass p, ending on a rest that fills the slot."""
    route = _route(p)
    k = int(rand(p, 1) * 10)
    picks = [tuple(_EVENTS)[int(rand(p, 30 + i) * len(_EVENTS))] for i in range(0 if k < 1 else 1 if k < 5 else 2)]
    line = _HOP + _PAN + _EDGE
    n = max(len(route), int((_PASS - _REST - sum(_EVENTS[e] for e in picks)) / line))   # repeat the route to fill
    events = {int(rand(p, 10 + i) * n): (0.3 + rand(p, 20 + i) * 0.4, e) for i, e in enumerate(picks)}
    beats, pos = [], (0.0, 0.0)

    def go(kind, to, dur):
        nonlocal pos
        beats.append((kind, pos, to, dur))
        pos = to

    for i in range(n):
        a, b = route[i % len(route)]
        go("hop", a, _HOP)
        f, e = events.get(i, (1.0, None))
        q = _lerp(a, b, f)
        if e and e != "ping":
            go("pan", q, _PAN * f)
            if e == "error":                      # read fails -- glitch, back to the start, scan it again
                go("error", q, 0.35)
                go("hop", a, 0.15)
                q, f = b, 0.0
            elif e == "rescan":                   # tick back over the last stretch, then forward again
                go("rescan", _lerp(a, b, f * 0.5), 0.25)
                go("rescan", q, 0.25)
            elif e == "startle":                  # what was THAT -- a far corner, then back
                go("startle", ((22.0, -22.0)[rand(p, 50) < 0.5], (9.0, -9.0)[rand(p, 51) < 0.5]), 0.35)
                go("hop", q, 0.2)
            else:
                go(e, q, _EVENTS[e])
        go("pan", b, _PAN * (1 - f) if e not in (None, "ping") else _PAN)
        go("ping" if e == "ping" else "edge", b, _EVENTS["ping"] if e == "ping" else _EDGE)
    out, t = [], 0.0
    for kind, frm, to, d in beats:
        out.append((t, kind, frm, to, d))
        t += d
    out.append((t, "rest", pos, (0.0, 0.0), _PASS - t))
    return tuple(out)


def _pose(now):
    p, t = int(now / _PASS), now % _PASS
    start, kind, frm, (gx, gy), dur = next(b for b in reversed(_plan(p)) if b[0] <= t)
    s = t - start
    if kind in ("pan", "rescan"):                 # quick discrete scanner steps, each snapping a hair past
        n = max(1, round(dur / _TICK))
        k = min(n, int(s / dur * n) + 1)
        u = (k + (_OVER if s - (k - 1) * dur / n < _KICK and k < n else 0)) / n
        return (*_lerp(frm, (gx, gy), u), _LOOK[kind])
    if kind == "error":                           # glitch: jittering gaze, flickering lids
        j = int(s * 25)
        return gx + (rand(p, j, 1) - 0.5) * 7, gy + (rand(p, j, 2) - 0.5) * 4, (0.35, 1.1)[j % 2]
    if kind == "lock":                            # freeze, open wide, squeeze down to focus
        return gx, gy, 1.2 - 0.6 * smoothstep(s / dur)
    if kind == "glance":                          # three quick darting looks
        j = min(2, int(s / dur * 3))
        return (rand(p, start, j) - 0.5) * 2 * _X, (rand(p, start, j, 1) - 0.5) * 2 * _Y, _LOOK[kind]
    if kind == "ping":                            # scan complete: a quick double blink
        return gx, gy, 0.12 if 0.05 < s < 0.13 or 0.22 < s < 0.3 else _LOOK["edge"]
    if kind == "rest":                            # centred beat: short looks, maybe a blink
        if rand(p, 9) < 0.6 and 0.2 < s < 0.35:
            return 0.0, 0.0, 0.12
        j = int(s / 0.5)
        return (rand(p, 60, j) - 0.5) * 8, (rand(p, 61, j) - 0.5) * 4, _LOOK[kind]
    if s < _KICK * 2:                             # overshoot the hop, the ease settles it back
        gx, gy = gx + (gx - frm[0]) * _OVER, gy + (gy - frm[1]) * _OVER
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
