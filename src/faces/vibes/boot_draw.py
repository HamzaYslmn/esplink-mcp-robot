"""Boot sequence -- a blinking cursor, then a scanline wipes down and the eyes 'draw in' row by
row. One-shot: it plays once and self-ends back to the normal face. The wipe just masks the
engine's eyes below the moving line."""
from ..spec import Vibe

_CURSOR = 1.0                                          # blinking-cursor beat
_WIPE = 1.6                                            # scanline reveal
_DONE = _CURSOR + _WIPE                                # fully drawn -> end

_state = {"start": None, "last": -1.0}                 # a >0.5s gap means a fresh boot


def _elapsed(now):
    """Seconds since this boot began (a gap restarts the clock)."""
    s = _state
    if s["start"] is None or now - s["last"] > 0.5 or now < s["last"]:
        s["start"] = now
    s["last"] = now
    return now - s["start"]


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    t = _elapsed(now)
    if t < _CURSOR:                                    # blank screen + blinking block cursor
        d.rectangle([0, 0, W - 1, H - 1], fill=0)
        if int(now * 2) % 2 == 0:
            d.rectangle([6, H - 12, 14, H - 6], fill=1)
    elif t < _DONE:                                    # scanline wipe reveals the eyes top-down
        y = int((t - _CURSOR) / _WIPE * H)
        d.rectangle([0, y, W - 1, H - 1], fill=0)      # everything below is still 'undrawn'
        d.line([0, y, W - 1, y], fill=1)               # the bright scan line
    # t >= _DONE: fully drawn -> _expired hands back to the normal face


def _expired(now, start):
    return _elapsed(now) >= _DONE


VIBE = Vibe("boot_draw", mood="neutral", overlay=_overlay, expired=_expired)
