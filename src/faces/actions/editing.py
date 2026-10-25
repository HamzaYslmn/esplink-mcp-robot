"""Two small chibi hands tap the keys -- editing (gaze stays put)."""
import math

from ..spec import Action


def _overlay(d, W, H, now, ox=0.0, oy=0.0):  # two small chibi hands tap the keys -- "editing"
    base = H - 3                                          # key row the fingertips reach
    for i, cx in enumerate((18, W - 18)):               # left & right hand, near the edges
        tap = round((math.sin(now * 8 + i * math.pi) + 1) / 2 * 3)   # alternating peck
        cy = base - 6 + tap                             # whole hand dips to press
        thumb = cx + (7 if i == 0 else -7)              # thumb tucked toward the centre
        d.ellipse([thumb - 2, cy - 3, thumb + 3, cy + 2], fill=1)    # thumb nub
        d.rounded_rectangle([cx - 7, cy - 5, cx + 7, cy + 2], radius=3, fill=1)  # back of hand
        for k in range(4):                              # four little fingertips on the keys
            fx = cx - 5 + k * 4
            d.ellipse([fx - 2, cy, fx + 2, cy + 5], fill=1)
        for k in range(3):                              # notches between the fingers
            nx = cx - 3 + k * 4
            d.line([nx, cy + 1, nx, cy + 5], fill=0, width=1)


ACTION = Action("editing", mood="focused", overlay=_overlay)
