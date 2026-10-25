"""Cylon / Knight Rider eye -- a red-scanner sweep: a row of LED segments with a bright lens gliding
back and forth across the bare panel (no visor frame). The lens travels at near-constant speed and
only eases gently at the turns, and its afterglow swings smoothly to the trailing side as it
reverses -- no dwell, no jolt, a seamless loop. Ordered (Bayer) dither renders the glow as a clean
gradient on 1-bit, not speckle. The overlay IS the whole eye."""
import math

from ..spec import Vibe

_MID = 32                    # scanner centre line
_HH = 9                      # beam max half-height
_X0, _X1 = 14, 114           # first / last segment centre
_STEP = 6                    # LED segment spacing -> the segmented KITT look
_REACH = 20.0                # glow half-width (px) at the turns
_SHARP = 1.4                 # how strongly the afterglow favours the trailing side
_SHAPE = 0.92                # 0->pure sine (dwells at ends); ->1 rounded triangle (constant speed)

# 4x4 Bayer matrix -> ordered dither thresholds; a smooth gradient instead of noisy speckle.
_BAYER = [[(v + 0.5) / 16.0 for v in row] for row in (
    (0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))]

_SEGS = list(range(_X0, _X1 + 1, _STEP))
_MIDX = (_X0 + _X1) / 2
_SPAN = (_X1 - _X0) / 2
_ASIN_K = math.asin(_SHAPE)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    d.rectangle([0, 0, W - 1, H - 1], fill=0)                  # the scanner owns the whole face

    t = now * 1.7                                             # ~3.7s round trip, loops on sin
    u = math.asin(_SHAPE * math.sin(t)) / _ASIN_K            # rounded triangle: near-constant speed
    sweep = _MIDX + u * _SPAN
    vn = math.cos(t)                                         # velocity direction, smooth through 0

    for sx in _SEGS:
        s = sx - sweep
        side = s * vn / _REACH                                # >0 ahead of travel, <0 trailing
        reach = _REACH * (0.55 + 0.95 / (1.0 + math.exp(side * _SHARP)))   # longer behind, smoothly
        g = math.exp(-(s / reach) ** 2)                       # bloom of this segment, 0..1
        if g < 0.06:
            continue
        hh = int(_HH * (0.4 + 0.6 * g))                       # tall at the lit core, short at the ends
        for y in range(_MID - hh, _MID + hh + 1):
            vy = 1.0 - abs(y - _MID) / (hh + 0.5)             # vertical taper -> rounded segment
            lit = g * (0.5 + 0.5 * vy)
            for x in (sx - 1, sx, sx + 1):                    # 3px-wide LED bar
                if lit > _BAYER[y & 3][x & 3]:
                    d.point((x, y), fill=1)

    cx = int(sweep)                                           # blazing solid core
    d.rectangle([cx - 1, _MID - _HH, cx + 1, _MID + _HH], fill=1)


VIBE = Vibe("cylon", mood="alert", overlay=_overlay, still=True)
