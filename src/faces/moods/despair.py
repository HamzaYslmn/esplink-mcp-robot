"""Drained slit -- hope gone."""
from ..painters import lids
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # drained slit
    lids(d, x, y, w, h, 0.42, 0.62)


MOOD = Mood("despair", dw=-8, dh=-6, paint=_paint)
