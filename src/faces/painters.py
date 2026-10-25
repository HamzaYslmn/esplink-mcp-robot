"""Shared mood drawing helpers: lid shapes a mood's `paint` carves (fill=0) onto a rounded-rect
eye, plus the little twinkle motif a couple of moods' decor reuse. Single-use helpers live
inline in their own effect file; these are the ones more than one mood builds on."""
from __future__ import annotations

import math


def brow(d, x, y, w, h, inner, outer, is_right):
    """Slanted top lid: covers to inner*h toward the nose, outer*h on the outside."""
    rt = y + h * (outer if is_right else inner)
    lt = y + h * (inner if is_right else outer)
    d.polygon([(x - 2, y - 2), (x + w + 2, y - 2), (x + w + 2, rt), (x - 2, lt)], fill=0)


def glare(d, x, y, w, h, depth, is_right):
    """Inner-down brow: a triangle whose tip drops to depth*h toward the nose."""
    tip = (x - 2, y + h * depth) if is_right else (x + w + 2, y + h * depth)
    d.polygon([(x - 2, y - 2), (x + w + 2, y - 2), tip], fill=0)


def lids(d, x, y, w, h, top=0.0, bottom=1.0):
    """Flat lids: cover down to top*h and up from bottom*h."""
    if top:
        d.rectangle([x - 1, y - 1, x + w + 1, y + h * top], fill=0)
    if bottom < 1:
        d.rectangle([x - 1, y + h * bottom, x + w + 1, y + h + 1], fill=0)


def sparkle(d, cx, cy, s):
    """4-point twinkle centred at (cx, cy)."""
    R, r = s, s * 0.34
    pts = [(cx + (R if k % 2 == 0 else r) * math.cos(-math.pi / 2 + k * math.pi / 4),
            cy + (R if k % 2 == 0 else r) * math.sin(-math.pi / 2 + k * math.pi / 4))
           for k in range(8)]
    d.polygon(pts, fill=1)
