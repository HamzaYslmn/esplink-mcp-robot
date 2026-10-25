"""Open eyes + concerned brow."""
from ..painters import brow
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # raised inner brow
    brow(d, x, y, w, h, 0.02, 0.26, ir)


MOOD = Mood("worried", dh=2, paint=_paint)
