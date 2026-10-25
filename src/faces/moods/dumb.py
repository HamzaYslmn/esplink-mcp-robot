"""A vacant glint punched out of each eye."""
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # punch a glint out of each eye
    g = max(2.0, w * 0.2)
    d.ellipse([x + w * 0.22, y + h * 0.2, x + w * 0.22 + g, y + h * 0.2 + g], fill=0)


MOOD = Mood("dumb", dw=4, dh=4, paint=_paint)
