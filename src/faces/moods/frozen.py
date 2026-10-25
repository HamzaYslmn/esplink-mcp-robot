"""Frozen -- minimal and cold. Clean ice eyes with one crisp glint; on entry a thin ice drape forms
along each eye and three icicles grow down from it. Then it's quiet: a soft light sweeps across the
ice every few seconds, one teardrop drips from each eye, a little snow drifts, Pip shivers faintly."""
import math

from ..primitives import flip, rand, smoothstep
from ..spec import Mood

_EYES = ((41, 32), (87, 32))                      # resting eye centres, before the gaze offset
_HALF_W, _HALF_H = 17, 15                         # eye half-size with dw=-2, dh=-6
_FREEZE_S = 4.0                                   # seconds for the icicles to grow in
_G = 140                                          # px/s^2 -- a falling drip
_ICICLES = (((-9, 8, 4), (0, 13, 5), (9, 6, 3)),  # per eye: (x offset, length, width) -- uneven, not mirrored
            ((-8, 6, 3), (2, 12, 5), (10, 9, 4)))
_DRIP = 2.8                                       # s per drip, from each eye's longest icicle

_state = {"start": None, "last": -1.0}            # a >0.5s gap = a fresh freeze


def _paint(d, x, y, w, h, r, ir):                 # one cold glint: two short parallel slashes
    if h < 10:
        return
    gx, gy = x + w * (0.22 if ir else 0.6), y + h * 0.18
    for k in (0, 3):
        d.line([(gx + k, gy + 6), (gx + 5 + k, gy)], fill=0)


def _icicle(d, x, top, ln, wd):
    """Tapered to a needle tip, with a carved glassy streak on the thick ones."""
    n = max(2, int(ln))
    left = [(x - wd / 2 * (1 - i / n) ** 0.85, top + i / n * ln) for i in range(n + 1)]
    right = [(2 * x - px, py) for px, py in left]
    d.polygon(left + right[::-1], fill=1)
    if wd >= 5 and ln > 6:
        d.line([(x - 1, top + 1), (x - 0.5, top + ln * 0.5)], fill=0)


def _drip(d, x, tip, phase, H):
    """Swell into a teardrop, let go, stretch as it falls."""
    u = (phase / _DRIP) % 1.0
    if u < 0.62:
        k = u / 0.62
        r = 1.5 * smoothstep(k)
        if r > 0.3:
            d.ellipse([x - r, tip + 1, x + r, tip + 1 + 2 * r * (1 + 1.3 * k ** 3)], fill=1)
        return
    t = (u - 0.62) * _DRIP
    y = tip + 4 + 0.5 * _G * t * t
    if y < H:
        d.line([(x, y), (x, y + 1 + _G * t * 0.03)], fill=1)


def _decor(d, W, H, now, ox=0.0, oy=0.0):
    st = _state
    if st["start"] is None or now - st["last"] > 0.5 or now < st["last"]:
        st["start"] = now                         # fresh freeze
    st["last"] = now
    f = smoothstep((now - st["start"]) / _FREEZE_S)
    for e, (ex, ey) in enumerate(_EYES):
        cx, top, base = ex + ox, ey + oy - _HALF_H, ey + oy + _HALF_H
        for xx in range(int(cx) - 15, int(cx) + 16):   # a thin wavy ice drape on the lower edge
            d.line([(xx, base - 1), (xx, base + f * (1 + 0.8 * math.sin(xx * 0.7 + cx)))], fill=1)
        for dx, ln, wd in _ICICLES[e]:
            _icicle(d, cx + dx, base + 1, ln * f, wd)
        if f > 0.95:
            dx, ln, _ = max(_ICICLES[e], key=lambda i: i[1])
            _drip(d, cx + dx, base + 1 + ln, now + e * 1.4, H)
        sweep = (now % 6.0) / 0.7                  # every 6 s a soft light sweeps across the ice
        if sweep < 1:
            gx = cx - _HALF_W - 10 + sweep * (2 * _HALF_W + 20)
            d.line([(gx, top + 2), (gx - 9, base - 2)], fill=0)
    for i in range(7):                            # a little slow snow, flipped so it shows over the eyes
        y = (now * (4 + 3 * rand(i, 4)) + rand(i, 5) * 72) % 72 - 4
        flip(d, rand(i, 6) * W + math.sin(now * 0.8 + i) * 2, y)


MOOD = Mood("frozen", dw=-2, dh=-6, sway=(0.35, 28), still=True, paint=_paint, decor=_decor)   # sway = a shiver
