"""Pure, stateless eye math + draw primitives -- shared by the engine and every effect. Imports
nothing else from the package, so any effect can `from ..primitives import smoothstep` with no
import cycle. (Effect-specific motion/draw logic stays in each effect's own file.)"""
from __future__ import annotations

import math
from functools import cache

from PIL import Image, ImageChops


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


def look(dx, dy, bias=0.0):
    """A glance motion: dart to (dx, dy), parallax-swell the near eye, hold, then return.
    Returns a gesture motion fn(p, env); shared by the look_left/right/up/down gestures."""
    def fn(p, e):
        hold = smoothstep(min(p / 0.22, 1.0, (1.0 - p) / 0.20))   # quick dart out, hold, quick return
        s = 1.0 - 0.12 * hold                 # mild foreshorten (parallax carries the turn)
        return dx * hold, dy * hold, 0.0, s, s, bias * hold
    return fn


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


def flip(d, x, y):
    """Invert one pixel, so a speck (rain, snow, a splash) shows on the black screen AND over a lit eye."""
    img, x, y = frame(d), int(round(x)), int(round(y))
    if img is not None and 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), 0 if img.getpixel((x, y)) else 1)


_BAYER = (0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5)


@cache
def _screen(w, h):
    t = Image.new("L", (w, h))
    t.putdata([_BAYER[(y % 4) * 4 + x % 4] * 16 + 8 for y in range(h) for x in range(w)])
    return t


def halftone(grey):
    """A grey 'L' image -> a '1' mask lit in proportion to its grey, by ordered dither: a stable pattern
    that doesn't crawl from frame to frame -- the 1-bit panel's way of showing soft light or haze."""
    return ImageChops.subtract(grey, _screen(*grey.size)).point(lambda v: 255 if v else 0).convert("1")


@cache
def _soft():
    g = Image.new("L", (64, 64))
    g.putdata([round(255 * max(0.0, 1 - math.hypot(x - 31.5, y - 31.5) / 32) ** 1.7)
               for y in range(64) for x in range(64)])
    return g


def soft_spot(g, x, y, rx, ry, k, add=False):
    """Paint a soft round blob of strength k (0..1) and radii rx, ry centred on (x, y) into grey image g,
    keeping the brighter of it and what's there -- or, with add, summing, so overlapping puffs thicken."""
    if k <= 0.01 or rx < 0.5 or ry < 0.5:
        return
    s = _soft().resize((max(1, round(2 * rx)), max(1, round(2 * ry))), Image.BILINEAR).point(lambda v: v * k)
    box = (round(x - rx), round(y - ry))
    under = g.crop((*box, box[0] + s.width, box[1] + s.height))
    g.paste((ImageChops.add if add else ImageChops.lighter)(under, s), box)
