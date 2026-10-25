"""Eyes dissolve, then reassemble as Pip himself drawn in ASCII art -- a little bot head whose two
`[o]` eyes land where the real eyes sit (Pip has no mouth, so neither does his portrait) -- hold,
then scatter back to natural. Plays ONCE, ~3s, then self-ends to natural eyes. (An action, not a
gesture: gestures can't draw, and this needs an overlay.) Each glyph flies in from a random
direction to its grid cell, staggered, so the face self-assembles instead of just fading in."""
import math

from PIL import ImageFont

from ..primitives import rand, smoothstep
from ..spec import Vibe

# the character, monospace grid -- two bracket eyes on a framed head, no mouth (the eyes ARE Pip)
_ART = (
    ".------------.",
    "|            |",
    "| [o]    [o] |",
    "|            |",
    "'------------'",
)
_CELL_W, _CELL_H = 7, 11                 # px per glyph cell (tuned so the [o] eyes line up with real eyes)
_ARTW, _ARTH = len(_ART[0]) * _CELL_W, len(_ART) * _CELL_H
_GLYPHS = tuple((ch, c * _CELL_W, r * _CELL_H)         # (char, x, y) of every non-blank cell
                for r, line in enumerate(_ART)
                for c, ch in enumerate(line) if ch != " ")

_IN, _HOLD, _OUT = 1.0, 1.0, 1.0                       # s: assemble / hold the face / scatter -- 3s total
_DUR = _IN + _HOLD + _OUT
_FLY = 30.0                                            # px a glyph flies in from while assembling
_start = [0.0]                                         # this run's start clock (captured each frame by _done)

try:
    _F = ImageFont.load_default(size=10)
except TypeError:                       # ancient Pillow
    _F = ImageFont.load_default()


def _done(now, start):
    """Self-end after one ~3s pass; also stash the start so pose/overlay can phase off elapsed time."""
    _start[0] = start
    return now - start >= _DUR


def _phase(now):
    """0 = solid eyes, 1 = full ASCII face; ramps up, plateaus through the hold, ramps back."""
    t = now - _start[0]
    if t < _IN:
        return smoothstep(t / _IN)
    t -= _IN
    if t < _HOLD:
        return 1.0
    t -= _HOLD
    return 1.0 - smoothstep(t / _OUT)


def _pose(now):
    return 0.0, 0.0, 1.0 - 0.92 * _phase(now)         # real eyes melt down as the glyphs take over


def _collapse_eyes(d, m, ox, oy):
    """Erase the real eyes' outer wings, narrowing them to nothing as m->1 (pose melts height,
    this melts width) -- so the held ASCII face sits on a clean panel, no leftover bars."""
    keep = 18.0 * (1.0 - m)                            # visible half-width per eye -> 0 as glyphs win
    for cx in (41 + ox, 87 + ox):                      # the two resting eye centres
        d.rectangle([cx - 19, 13 + oy, cx - keep, 51 + oy], fill=0)
        d.rectangle([cx + keep, 13 + oy, cx + 19, 51 + oy], fill=0)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    m = _phase(now)
    if m < 0.02:
        return
    _collapse_eyes(d, m, ox, oy)
    x0 = (W - _ARTW) / 2 + ox
    y0 = (H - _ARTH) / 2 + oy
    for ch, gx, gy in _GLYPHS:
        a = rand(gx, gy)                              # staggered arrival: each glyph settles at its own m
        local = smoothstep((m - a * 0.5) / 0.5)
        if local < 0.02:
            continue
        ang = rand(gx, gy, 7) * math.tau
        dist = (1.0 - local) * _FLY                   # fly in from a random direction, home in as it settles
        d.text((x0 + gx + math.cos(ang) * dist, y0 + gy + math.sin(ang) * dist), ch, font=_F, fill=1)


VIBE = Vibe("ascii_morph", mood="neutral", pose=_pose, overlay=_overlay, expired=_done, still=True)
