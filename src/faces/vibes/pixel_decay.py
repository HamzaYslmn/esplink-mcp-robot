"""Pixel decay -- the eyes crumble to sand, once, and stay. Pixels flake off ONE AT A TIME (random
order, not in rows), fall under gravity, and the wind carries them across the full-width ground
into drifting dunes. The sand is then conserved and endlessly reshaped: the wind keeps lifting
grains off the dune crests and dropping them downwind, so a grain added here is one taken from
there -- the dunes migrate and never tower. Plays ONCE: it does not loop or reform; re-firing the
activity (a >0.5s gap) restarts the crumble."""
import math

from ..primitives import rand
from ..spec import Vibe

_EYE_TOP, _EYE_BOT = 14, 50
_L0, _L1, _R0, _R1 = 23, 59, 69, 105               # the two eye x-spans (engine defaults)
_GROUND, _FLOOR = 63, 62                            # ground line / top row sand rests on
_G = 48.0          # gravity px/s^2 -- gentle, the fall is watchable
_DRAG = 1.8        # air drag on flying grains
_SLOPE = 1         # angle of repose (max stable neighbour step) -> low, wide dunes
_DISS = 8.0        # s to fully crumble the eyes
_GRAIN_P = 0.22    # fraction of flaked pixels that become real sand (keeps the dunes low)
_SALT = 2          # grains the wind lifts off the crests per frame (saltation -> migration)


def _eye_pixels():
    """Every eye pixel, in a fixed shuffled order -- the order they flake off."""
    px = [(x, y) for a, b in ((_L0, _L1), (_R0, _R1))
          for x in range(a, b + 1) for y in range(_EYE_TOP, _EYE_BOT + 1)]
    px.sort(key=lambda p: rand(p[0], p[1]))
    return px


_EYEPIX = _eye_pixels()
_NPIX = len(_EYEPIX)

_grains = []           # flying grains [x, y, vx, vy]
_pile = [0] * 128      # sand height per column (full-width ground)
_removed = [0]         # eye pixels flaked so far (index into _EYEPIX)
_t0 = [None]           # crumble start time
_last = [None]         # previous now (dt + gap detect)


def _wind(now):
    return 22.0 * math.sin(now * 0.13) + 9.0 * math.sin(now * 0.47 + 1.3)   # slow reverse + gusts


def _reset(now):
    _removed[0] = 0
    _grains.clear()
    for i in range(128):
        _pile[i] = 0
    _t0[0] = now


def _settle(gx):
    """Drop a grain on column gx, rolling it downhill until the slope is stable (angle of repose)."""
    guard = 0
    while guard < 60:
        guard += 1
        opts = []
        if gx > 0 and _pile[gx] - _pile[gx - 1] > _SLOPE:
            opts.append((_pile[gx - 1], gx - 1))
        if gx < 127 and _pile[gx] - _pile[gx + 1] > _SLOPE:
            opts.append((_pile[gx + 1], gx + 1))
        if not opts:
            break
        gx = min(opts)[1]
    _pile[gx] += 1


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    prev = _last[0]
    if prev is None or now - prev > 0.5 or now < prev:     # first frame / re-fire -> restart
        _reset(now)
        prev = now
    _last[0] = now
    dt = min(0.1, now - prev)
    w = _wind(now)

    target = min(_NPIX, int((now - _t0[0]) / _DISS * _NPIX))   # crumble pixels up to the time budget
    while _removed[0] < target:
        x, y = _EYEPIX[_removed[0]]
        _removed[0] += 1
        if rand(x, y, 9) < _GRAIN_P:
            _grains.append([float(x), float(y), 0.0, 5.0])

    if _removed[0] > _NPIX * 0.12:                          # saltation: wind lifts crests, drops downwind
        for s in range(_SALT):
            cols = [int(rand(int(now * 90), s, i) * 128) for i in range(4)]
            x = max(cols, key=lambda c: _pile[c])          # erode the tallest of a few random columns
            if _pile[x] > 0:
                _pile[x] -= 1
                _grains.append([float(x), float(_FLOOR - _pile[x]), w * 0.25, -8.0])   # hop into the wind

    landed = []                                            # physics: gravity + wind + drag, wrap at edges
    for g in _grains:
        g[3] += _G * dt
        g[2] += w * dt
        g[2] -= g[2] * _DRAG * dt
        g[0] = (g[0] + g[2] * dt) % 128
        g[1] += g[3] * dt
        xi = int(g[0])
        if g[1] >= _FLOOR - _pile[xi]:
            _settle(xi)
            landed.append(g)
    for g in landed:
        _grains.remove(g)

    if _removed[0] >= _NPIX:                                # erase what's gone to sand
        d.rectangle([_L0, _EYE_TOP, _L1, _EYE_BOT], fill=0)
        d.rectangle([_R0, _EYE_TOP, _R1, _EYE_BOT], fill=0)
    else:
        d.point(_EYEPIX[:_removed[0]], fill=0)

    d.line([0, _GROUND, 127, _GROUND], fill=1)             # the full-width ground
    if _grains:
        d.point([(g[0], g[1]) for g in _grains], fill=1)   # grains in flight
    for x in range(128):                                   # the dunes
        if _pile[x] > 0:
            d.line([x, _FLOOR, x, _FLOOR - _pile[x] + 1], fill=1)


VIBE = Vibe("pixel_decay", mood="neutral", overlay=_overlay, still=True)
