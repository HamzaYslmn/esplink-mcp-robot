"""Nod along under the headphones -- listening."""
import math

from ..spec import Action


def _pose(now):   # attentive, gently nodding along under the headphones
    return math.sin(now * 1.8) * 2, math.sin(now * 3.6) * 2, 1.0


def _overlay(d, W, H, now, ox=0.0, oy=0.0):  # band + an ear cup each side -- "listening"
    cw, ch = 11, 22
    cy = H // 2 - ch // 2
    d.rounded_rectangle([2, cy, 2 + cw, cy + ch], radius=4, fill=1)          # left cup
    d.rounded_rectangle([W - 3 - cw, cy, W - 3, cy + ch], radius=4, fill=1)  # right cup
    d.arc([8, 1, W - 9, H - 12], start=180, end=360, fill=1, width=3)        # headband


ACTION = Action("listening", mood="attentive", pose=_pose, overlay=_overlay)
