"""Quick wandering glances + a magnifier sweep -- searching."""
import math

from ..spec import Action


def _pose(now):   # quick wandering glances -- scanning results
    return math.sin(now * 2.2) * 11 + math.sin(now * 1.3) * 5, math.sin(now * 1.7) * 5, 1.0


def _overlay(d, W, H, now, ox=0.0, oy=0.0):  # a magnifying glass sweeps across -- "searching"
    rad = 6
    cx = W / 2 + math.sin(now * 1.6) * (W / 2 - 12)
    cy = H - 11 + math.sin(now * 3.2) * 2
    d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=1, width=2)  # lens rim
    hx, hy = cx + rad * 0.7, cy + rad * 0.7
    d.line([hx, hy, hx + 5, hy + 5], fill=1, width=2)                        # handle


ACTION = Action("searching", mood="focused", pose=_pose, overlay=_overlay)
