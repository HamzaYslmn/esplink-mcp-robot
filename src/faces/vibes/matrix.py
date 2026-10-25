"""Code rain -- Pip jacked into the matrix: glyph columns stream down past the eyes."""
from PIL import ImageFont

from ..primitives import rand
from ..spec import Vibe

_CHARS = "01<>*+=$#%&8Z7XK"
_STEP = 8           # column spacing (px)
_CH = 9             # glyph cell height (px)
_TAIL = 6           # glyphs per falling stream

try:
    _FONT = ImageFont.load_default(size=9)
except TypeError:                       # ancient Pillow
    _FONT = ImageFont.load_default()


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    span = H + _TAIL * _CH
    for c in range(W // _STEP):
        x = c * _STEP + 1
        head = (now * (16 + rand(c) * 34) + rand(c, 1) * span) % span    # per-column fall, wraps
        for k in range(_TAIL):
            y = head - k * _CH
            if -_CH < y < H:
                ch = _CHARS[int(rand(c, k, int(now * 5)) * len(_CHARS))]  # glyphs flicker as they fall
                d.text((x, y), ch, font=_FONT, fill=1)


VIBE = Vibe("matrix", mood="focused", overlay=_overlay)
