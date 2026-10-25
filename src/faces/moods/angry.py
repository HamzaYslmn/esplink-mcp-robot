"""Inner-down glare."""
from ..painters import glare
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # glare
    glare(d, x, y, w, h, 0.60, ir)


MOOD = Mood("angry", paint=_paint)
