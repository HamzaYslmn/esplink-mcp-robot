"""Narrow slit eyes -- side-eye."""
from ..painters import lids
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # heavy slit + pinched bottom -- side-eye
    lids(d, x, y, w, h, 0.40, 0.88)


MOOD = Mood("suspicious", dw=-2, paint=_paint)
