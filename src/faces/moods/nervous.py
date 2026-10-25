"""Anxious brow + a sweat bead."""
from ..painters import brow
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # raised inner brow
    brow(d, x, y, w, h, 0.02, 0.26, ir)


def _decor(d, W, H, now, ox=0.0, oy=0.0):  # a nervous bead wells up by the brow then slides -- "nervous"
    t = (now * 0.8) % 1.0
    x, y, s = W - 16 + int(ox), 8 + t * 11, 3
    d.ellipse([x - s * 0.7, y - s * 0.3, x + s * 0.7, y + s], fill=1)             # rounded body
    d.polygon([(x, y - s - 3), (x - s * 0.6, y - s * 0.2), (x + s * 0.6, y - s * 0.2)], fill=1)  # pointed top


MOOD = Mood("nervous", dw=-2, paint=_paint, decor=_decor)
