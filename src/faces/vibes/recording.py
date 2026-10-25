"""Recording -- a blinking REC dot and a running mm:ss timer."""
from PIL import ImageFont

from ..spec import Vibe

try:
    _F = ImageFont.load_default(size=9)
    _FT = ImageFont.load_default(size=13)
except TypeError:                       # ancient Pillow
    _F = _FT = ImageFont.load_default()

_state = {"start": None, "last": -1.0}  # a >0.5s gap means a fresh recording


def _elapsed(now):
    s = _state
    if s["start"] is None or now - s["last"] > 0.5 or now < s["last"]:
        s["start"] = now
    s["last"] = now
    return now - s["start"]


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    if (now * 1.4) % 1.0 < 0.6:                       # ~1.4 Hz blink
        d.ellipse([6, 4, 14, 12], fill=1)
    d.text((18, 3), "REC", font=_F, fill=1)
    t = int(_elapsed(now))
    ts = f"{t // 60:02d}:{t % 60:02d}"
    d.text(((W - d.textlength(ts, font=_FT)) / 2, H - 15), ts, font=_FT, fill=1)


VIBE = Vibe("recording", mood="alert", overlay=_overlay)
