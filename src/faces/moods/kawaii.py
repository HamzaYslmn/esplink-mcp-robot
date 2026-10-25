"""Round eyes + rosy blush hatch + twinkles -- kawaii."""
from ..painters import sparkle
from ..spec import Mood


def _decor(d, W, H, now, ox=0.0, oy=0.0):  # rosy blush hatch + twinkles -- "kawaii"
    for cx in (14, W - 24):                                    # a blush patch under each eye -- tracks the gaze
        for i in range(3):
            d.line([cx + i * 4 + ox, H - 12 + oy, cx + 3 + i * 4 + ox, H - 7 + oy], fill=1, width=1)
    for fx, fy, s in ((0.07, 0.16, 4), (0.93, 0.18, 4), (0.5, 0.06, 3)):
        sparkle(d, fx * W, fy * H, s)                          # ambient twinkles stay put


MOOD = Mood("kawaii", dw=2, dh=0, decor=_decor)
