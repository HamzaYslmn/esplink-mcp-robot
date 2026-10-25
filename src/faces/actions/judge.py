"""Order in the court (Higuruma's gavel) -- judging, as a looping status. The bench slides in from
the right and the eyes slide left to face it, then rounds play back to back, each a fresh scene: a
lone rap, a double tap, an escalating volley, a slow trembling verdict, or a frenzy of blows --
the eyes leaning in on the wind-up and flinching on the hit.

Self-check: `cd src && uv run python -m faces.actions.judge`."""
import math

from ..primitives import frame, rand, smoothstep
from ..spec import Action

_DUR = 3.8                     # s per round; every scene fits inside one
_SWING, _REBOUND = 0.13, 0.1   # s: slam down / bounce off the block
_STRIKE = 180.0                # handle angle (deg, y-up) flat on the block
_GX, _GY, _L = 124, 44, 22     # grip at the right edge, handle length
_BX, _BY = 102, 52             # strike point on the block top
_SLIDE = 0.4                   # s the bench takes to slide in
_SHIFT = -12.0                 # eyes' x while the bench is on screen


def _plan(seed):
    """One scene per trigger -> its hits. A hit = (time s, raised angle deg, raise s,
    hold s, power 0..1); power scales the wind-up and the impact."""
    j = lambda i, amt: (rand(seed, i) - 0.5) * amt          # per-trigger timing/height jitter
    kind = int(rand(seed) * 5)
    if kind == 0:                                           # a long stare, then a single firm rap
        return [(1.6 + j(1, 0.2), 115 + j(2, 10), 0.3, 0.15, 0.55)]
    if kind == 1:                                           # double tap
        return [(1.5, 120, 0.25, 0.08, 0.5), (1.85, 140 + j(2, 10), 0.1, 0.0, 0.6)]
    if kind == 2:                                           # order, order, ORDER
        return [(0.9, 115, 0.25, 0.08, 0.45), (1.5 + j(1, 0.1), 105, 0.25, 0.1, 0.65),
                (2.6, 100, 0.45, 0.4, 1.0)]
    if kind == 3:                                           # the verdict: one slow, trembling, heavy blow
        return [(2.1 + j(1, 0.3), 98, 0.6, 0.7, 1.0)]
    hits = [(0.8 + i * 0.26 + j(10 + i, 0.02), 140 + j(20 + i, 15), 0.1, 0.0, 0.5 + rand(seed, 30 + i) * 0.2)
            for i in range(5)]                              # frenzy: a flurry of short blows...
    return hits + [(hits[-1][0] + 0.75, 102, 0.3, 0.15, 0.9)]   # ...then one more for good measure


def _beat(t, seed):
    """(since last impact, last hit|None, until next impact, next hit|None) at t s into the play."""
    hits = _plan(seed)
    last = max((h for h in hits if h[0] <= t), key=lambda h: h[0], default=None)
    nxt = min((h for h in hits if h[0] > t), key=lambda h: h[0], default=None)
    return (t - last[0] if last else 9.9, last, nxt[0] - t if nxt else 9.9, nxt)


def _angle(t, seed):
    s, _, n, nxt = _beat(t, seed)
    rest = _STRIKE - 14 * math.sin(math.pi * s / _REBOUND) if s < _REBOUND else _STRIKE
    if nxt is None:
        return rest
    _, top, rise, hold, power = nxt
    if n < _SWING:                                          # slam: accelerates into the block
        return top + (_STRIKE - top) * (1 - n / _SWING) ** 2
    if n < _SWING + hold:                                   # poised overhead, trembling as hard as it'll hit
        return top + power ** 3 * 1.5 * math.sin(t * 70)
    if n < _SWING + hold + rise:                            # lifting (out of any rebound)
        return rest + (top - rest) * smoothstep(1 - (n - _SWING - hold) / rise)
    return rest


def _round(now):
    """(seconds into this round, this round's scene seed, 0..1 how far the bench has slid in)."""
    T, seed = getattr(now, "t", now), getattr(now, "seed", 0)
    k, t = divmod(T, _DUR)
    return t, int(rand(seed, k) * 1e6), smoothstep(T / _SLIDE)


def _moods(t, seed):
    """(impact jolt, wind-up lean) -- what the eyes and props key off."""
    s, last, n, nxt = _beat(t, seed)
    span = 0.15 + 0.25 * last[4] if last else 1.0
    k = (1 - s / span) * last[4] if last and s < span else 0.0
    lean = 0.0
    if nxt and _SWING < n < _SWING + nxt[2] + nxt[3]:       # building up through raise + hold
        lean = nxt[4] * smoothstep(1 - (n - _SWING) / (nxt[2] + nxt[3]))
    return k, lean


def _pose(now):   # face the bench; lean up on the wind-up, jolt + flinch on the hit
    t, seed, pres = _round(now)
    k, lean = _moods(t, seed)
    return _SHIFT * pres, 3 * k - 2 * lean, 1.0 + 0.04 * lean - 0.12 * k


def _gavel(d, ang, dx):
    a = math.radians(ang)
    ux, uy = math.cos(a), -math.sin(a)                      # handle direction (screen y-down)
    gx = _GX + dx
    hx, hy = gx + _L * ux, _GY + _L * uy                    # head centre
    px, py = -uy, ux                                        # head's long axis, across the handle
    pt = lambda u, v: (hx + px * u + ux * v, hy + py * u + uy * v)
    d.line([gx, _GY, hx, hy], fill=1, width=3)              # handle
    d.polygon([pt(-7, -5), pt(7, -5), pt(7, 5), pt(-7, 5)], fill=1)   # head
    for u in (-4, 4):                                       # dark bands by each striking face
        d.line([pt(u, -5), pt(u, 5)], fill=0)
    d.line([pt(-2, -5), pt(2, -5)], fill=0, width=2)        # collar where the handle seats
    d.ellipse([gx - 4, _GY - 4, gx + 5, _GY + 4], fill=1)   # fist


def _impact(d, s, hit, k, dx):
    """Burst lines, a ground shockwave ring, dust puffs and splinters -- all scaled by the hit's power."""
    p, q = hit[4], 1 - k / hit[4]                           # power, 0..1 progress through the impact
    bx = _BX + dx
    r, ln = 4 + (6 + 10 * p) * q, 3 + 4 * p
    for deg in (140, 160, 175, 5, 20, 40)[: 2 + round(4 * p)]:
        c, sn = math.cos(math.radians(deg)), -math.sin(math.radians(deg))
        d.line([bx + c * r, _BY - 2 + sn * r, bx + c * (r + ln), _BY - 2 + sn * (r + ln)],
               fill=1, width=2 if p > 0.8 else 1)
    if p > 0.6:                                             # shockwave rolling along the bench
        rx = 6 + 30 * q
        d.ellipse([bx - rx, 60 - rx / 5, bx + rx, 60 + rx / 5], outline=1)
    if p > 0.75:                                            # dust kicked up both sides of the block
        for side in (-1, 1):
            cx, cy, pr = bx + side * (13 + 14 * q), 57 - 5 * q, 1 + 3 * q
            d.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], outline=1)
    seed = int(hit[0] * 100)                                # same splinters through one hit
    for i in range(2 + round(8 * p)):
        vx, vy = (rand(seed, i, 1) - 0.5) * 70, 20 + rand(seed, i, 2) * 50 * p
        x, y = bx + vx * s, _BY - vy * s + 120 * s * s
        if y < _BY:
            d.rectangle([x, y, x + 1, y + 1], fill=1)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    t, seed, pres = _round(now)
    s, last, n, nxt = _beat(t, seed)
    k, _ = _moods(t, seed)
    dx = (1 - pres) * 44                                    # the bench slides in from the right
    d.rectangle([min(86 + dx, W - 1), 61, W - 1, H - 1], fill=1)   # the bench
    d.rounded_rectangle([91 + dx, 56, 113 + dx, 59], radius=1, fill=1)   # sound block base
    d.rounded_rectangle([94 + dx, _BY, 110 + dx, 55], radius=1, fill=1)  # ...and its top plate
    ang = _angle(t, seed)
    if nxt and n < _SWING and nxt[4] > 0.6:                 # swoosh trailing a heavy blow
        for r in (_L + 8, _L + 2):
            pts = [(_GX + dx + r * math.cos(math.radians(a)), _GY - r * math.sin(math.radians(a)))
                   for a in (nxt[1] + (ang - nxt[1]) * i / 8 for i in range(9))]
            d.line(pts, fill=1)
    _gavel(d, ang, dx)
    if k:
        _impact(d, s, last, k, dx)
    img = frame(d)
    if img is not None and k and last[4] > 0.5:             # screen shake, harder for heavier blows
        amp = 3 * last[4] * k
        sx, sy = round(amp * math.sin(t * 90)), round(amp * math.cos(t * 73))
        if sx or sy:
            snap = img.copy()
            d.rectangle([0, 0, W - 1, H - 1], fill=0)
            img.paste(snap, (sx, sy))
    if img is not None and last and last[4] >= 1.0 and s < 0.05:   # white-out flash on a full-power blow
        img.paste(img.convert("L").point(lambda v: 255 - v).convert("1"), (0, 0))


ACTION = Action("judge", mood="neutral", pose=_pose, overlay=_overlay)


if __name__ == "__main__":
    kinds = set()
    for seed in range(200):
        hits = _plan(seed)
        kinds.add(len(hits) * 10 + round(hits[-1][3] * 10))
        for h in hits:
            assert abs(_angle(h[0], seed) - _STRIKE) < 1, "every impact lands on the block"
        for a, b in zip(hits, hits[1:]):
            assert b[0] - a[0] >= _SWING + b[2] + b[3], "wind-up must fit between blows"
        assert hits[0][0] - _SWING - hits[0][2] - hits[0][3] >= _SLIDE * 0.5, "no swing before it's on screen"
        assert hits[-1][0] + 0.8 <= _DUR, "last blow settles before the next round starts"
    assert len(kinds) == 5, f"every scene should come up: {kinds}"
    from ..spec import Now
    rounds = {_round(Now(0.0, r * _DUR + 1, 7))[1] for r in range(20)}
    assert len(rounds) == 20, "a fresh scene every round"
    assert _round(Now(0.0, 0.0, 7))[2] == 0 and _round(Now(0.0, 9.0, 7))[2] == 1, "the bench slides in once, then stays"
    print("judge ok")
