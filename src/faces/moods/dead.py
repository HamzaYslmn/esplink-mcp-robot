"""KO -- an X carved across each eye."""
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # KO -- an X carved across the eye
    lw = max(2, int(w * 0.16))
    d.line([x + 3, y + 3, x + w - 4, y + h - 4], fill=0, width=lw)
    d.line([x + w - 4, y + 3, x + 3, y + h - 4], fill=0, width=lw)


MOOD = Mood("dead", paint=_paint)
