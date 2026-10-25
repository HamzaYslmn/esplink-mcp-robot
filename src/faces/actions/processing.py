"""Focused on the task: a steady determined look + a loading throbber spinning upper-right."""
import math

from ..spec import Action

_SPOKES = 12


def _pose(now):   # calm, locked-in focus -- a slow steady scan over the work
    return math.sin(now * 0.9) * 4, 2 + math.sin(now * 0.6), 0.9


def _overlay(d, W, H, now, ox=0.0, oy=0.0):  # a loading throbber spinning at the upper-right -- working
    cx, cy, r_in = W - 12, 12, 4
    lead = now * 1.1                                   # the bright head sweeps round ~1.1 turns/sec
    for i in range(_SPOKES):
        frac = i / _SPOKES
        tail = (frac - lead) % 1.0                     # 0 = the long bright head, ->1 trails behind it
        a = 2 * math.pi * frac
        ca, sa = math.cos(a), math.sin(a)
        r_out = r_in + 2 + 5 * (1 - tail)              # head spoke longest, shrinking round the ring
        d.line([cx + ca * r_in, cy + sa * r_in, cx + ca * r_out, cy + sa * r_out],
               fill=1, width=2 if tail < 0.5 else 1)   # leading spokes bold, trailing ones thin


ACTION = Action("processing", mood="focused", pose=_pose, overlay=_overlay)
