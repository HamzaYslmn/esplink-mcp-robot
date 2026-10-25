"""Determined band across the eyes."""
from ..painters import lids
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # determined band
    lids(d, x, y, w, h, 0.24, 0.76)


MOOD = Mood("focused", paint=_paint)
