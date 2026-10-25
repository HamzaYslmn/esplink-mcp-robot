"""Hooded, peering out."""
from ..painters import brow
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # hooded, peering out
    brow(d, x, y, w, h, 0.38, 0.52, ir)


MOOD = Mood("tired", paint=_paint)
