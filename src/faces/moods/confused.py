"""Only the lower (right) eye squints."""
from ..painters import lids
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # only the lower (right) eye squints
    if ir:
        lids(d, x, y, w, h, top=0.28)


MOOD = Mood("confused", tilt=4, paint=_paint)
