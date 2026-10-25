"""Flat half-lids."""
from ..painters import lids
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # flat half-lids
    lids(d, x, y, w, h, top=0.5)


MOOD = Mood("bored", paint=_paint)
