"""Heavy-lidded, mellow -- at ease."""
from ..painters import lids
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # heavy-lidded, mellow
    lids(d, x, y, w, h, top=0.45)


MOOD = Mood("chill", dh=-4, paint=_paint)
