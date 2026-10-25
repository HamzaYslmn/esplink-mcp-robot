"""Small + downcast."""
from ..painters import brow
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # downcast droop
    brow(d, x, y, w, h, 0.30, 0.66, ir)


MOOD = Mood("sad", dw=-4, dh=-6, paint=_paint)
