"""Pure, stateless eye math + draw primitives -- shared by the engine and every effect. Imports
nothing else from the package, so any effect can `from ..primitives import smoothstep` with no
import cycle. (Effect-specific motion/draw logic stays in each effect's own file.)"""
from __future__ import annotations

import math


def ease(cur, tgt, dt, tau):
    """Frame-rate-independent exponential approach of cur -> tgt."""
    return tgt + (cur - tgt) * math.exp(-dt / tau)


def smoothstep(k):
    """Hermite ease 0..1 with flat ends; clamps out-of-range input."""
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


_NOISE = (12.9898, 78.233, 37.719, 51.07, 19.33)     # value-noise coefficients (irrational-ish)


def rand(*xs):
    """The one deterministic pseudo-random for every effect: fixed inputs -> a fixed 0..1, stable
    every frame. Replaces the per-file `sin(x*12.9898)*43758.5453 % 1` lambdas -- pass a seed (and
    any salts) for an independent stream, e.g. rand(slot), rand(slot, i)."""
    return (math.sin(sum(x * k for x, k in zip(xs, _NOISE))) * 43758.5453) % 1.0


def lid_openness(u, reps, close=0.34):
    """Eyelid openness over a blink, 1->0->1 x reps; asymmetric -- snaps shut, eases open."""
    seg = (max(0.0, min(1.0, u)) * reps) % 1.0
    if seg < close:
        return 1.0 - smoothstep(seg / close)              # fast close
    return smoothstep((seg - close) / (1.0 - close))      # slower open


def rounded_rect(d, x, y, w, h, r, fill):
    """Rounded rect, clamped radius; rounds size once so a sub-pixel drift slides it rigidly."""
    if w <= 0 or h <= 0:
        return
    x0, y0 = round(x), round(y)
    x1, y1 = x0 + round(w) - 1, y0 + round(h) - 1
    if x1 < x0 or y1 < y0:
        return
    rr = max(0, min(int(r), (x1 - x0) // 2, (y1 - y0) // 2))
    if rr <= 0:
        d.rectangle([x0, y0, x1, y1], fill=fill)
    else:
        d.rounded_rectangle([x0, y0, x1, y1], radius=rr, fill=fill)


def frame(d):
    """The live PIL '1' buffer behind an effect's ImageDraw -- for overlays that read pixels back
    (datamosh, reel-cut). None-safe for any odd/headless draw target."""
    return getattr(d, "_image", None)
