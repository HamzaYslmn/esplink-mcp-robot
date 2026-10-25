"""Barcode scan -- a band of variable-width bars scrolls past while a bright sweep line tracks
across it. Eyes stay above, small."""
from ..primitives import rand
from ..spec import Vibe


def _pose(now):
    return 0.0, -7.0, 0.5          # eyes lifted above the band


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    y0, y1 = H - 24, H - 10
    off = int(now * 30)
    x, k = 4, 0
    while x < W - 4:
        w = 1 + int(rand((x + off) // 3) * 3)
        if k % 2 == 0:
            d.rectangle([x, y0, x + w - 1, y1], fill=1)
        x += w
        k += 1
    sx = (now * 60) % W                                        # sweep line
    d.line([sx, y0 - 3, sx, y1 + 3], fill=1)


VIBE = Vibe("barcode_scan", mood="focused", pose=_pose, overlay=_overlay, still=True)
