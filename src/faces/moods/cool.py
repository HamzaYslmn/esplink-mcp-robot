"""Pixel-art "deal-with-it" shades, no eyes -- wanders side to side like eyes."""
import math

from ..spec import Mood

# pixel-art "deal-with-it" shades; '#' = dark lens block, gaps inside a lens = the gleam
_SHADES_ART = (
    "################################",   # connected top bar
    "###############  ###############",   # center bridge notch
    " ## # ########    ## # ######## ",   # gleam streaks, lower-left of each lens
    "  ## # #######     ## # ######  ",
    "   ## # #####       ## # ####   ",
    "    ########         #######    ",   # angled lens bottoms
)
_SHADES_BLOCKS = [(c, r) for r, row in enumerate(_SHADES_ART)  # block (col, row) coords, scanned once
                  for c, ch in enumerate(row) if ch == "#"]


def _decor(d, W, H, now, ox=0.0, oy=0.0):  # pixel-art shades, no eyes -- wanders side to side like eyes
    u = 3                                                      # pixel-block size (96x48 -> leaves room to wander)
    sway = round(math.sin(now * 0.7) * 9 + math.sin(now * 1.7) * 4)   # organic side-to-side wander
    x0 = (W - len(_SHADES_ART[0]) * u) // 2 + sway
    y0 = (H - len(_SHADES_ART) * u) // 2 + round(math.sin(now * 0.9) * 2)  # a small vertical bob
    for c, r in _SHADES_BLOCKS:
        px, py = x0 + c * u, y0 + r * u
        d.rectangle([px, py, px + u - 1, py + u - 1], fill=1)


MOOD = Mood("cool", bare=True, decor=_decor)
