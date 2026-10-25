"""Cheeks-up smile."""
from ..spec import Mood


def _paint(d, x, y, w, h, r, ir):   # cheeks-up smile: round-ended dome, soft upward curve below
    d.ellipse([x - w * 0.55, y + h * 0.5, x + w * 1.55, y + h * 2.1], fill=0)


MOOD = Mood("happy", paint=_paint)
