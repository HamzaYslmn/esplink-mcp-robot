"""One eye narrowed + angled, the other barely lidded."""
from ..painters import brow, lids
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # one eye narrowed+angled, the other barely lidded
    if ir:
        lids(d, x, y, w, h, top=0.14)
    else:
        brow(d, x, y, w, h, 0.5, 0.66, False)   # slanted top lid -- a wary angle


MOOD = Mood("skeptical", paint=_paint)
