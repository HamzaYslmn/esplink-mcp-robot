"""Defrag -- a grid of cells packs in left-to-right (with a little shuffle noise running ahead of
the front), wraps, repeats. Eyes look up while it works the bottom band."""
from ..primitives import rand
from ..spec import Vibe

_COLS, _ROWS, _CELL = 16, 2, 6


def _pose(now):
    return 0.0, -6.0, 0.6          # glance up off the disk


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    x0 = (W - _COLS * _CELL) // 2
    y0 = H - _ROWS * _CELL - 2
    front = int(now * 4) % (_COLS * _ROWS + 8)                 # progress, with a pause each wrap
    for i in range(_COLS * _ROWS):
        cx, cy = x0 + (i % _COLS) * _CELL, y0 + (i // _COLS) * _CELL
        if i < front or rand(i, int(now * 3)) < 0.15:          # packed, plus a shuffle ahead
            d.rectangle([cx, cy, cx + _CELL - 2, cy + _CELL - 2], fill=1)
        else:
            d.point((cx, cy), fill=1)                          # empty-cell tick


VIBE = Vibe("defrag_blocks", mood="focused", pose=_pose, overlay=_overlay)
