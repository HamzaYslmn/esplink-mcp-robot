"""Now playing -- a little equalizer bouncing to the beat, with a music note."""
import math

from ..spec import Widget

_BARS = 15


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    gap = (W - 8) / _BARS
    for i in range(_BARS):
        h = 2 + (math.sin(now * (4 + (i % 5) * 1.7) + i) * 0.5 + 0.5) * 12   # per-bar bounce
        x = 4 + i * gap
        d.rectangle([x, H - h, x + 3, H - 1], fill=1)
    d.ellipse([6, 8, 11, 12], fill=1)                 # note head
    d.line([11, 10, 11, 2], fill=1)                   # stem
    d.line([11, 2, 15, 3], fill=1)                    # flag


WIDGET = Widget("now_playing", mood="happy", overlay=_overlay)
