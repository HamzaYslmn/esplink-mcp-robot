"""Leaned in, locked on -- "go ahead"."""
from ..painters import lids
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # crisp top lid -- locked on
    lids(d, x, y, w, h, top=0.12)


MOOD = Mood("attentive", dw=2, dh=2, paint=_paint)
