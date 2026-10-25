"""A centred terminal cursor that idly blinks and now and then types "waiting..." -- waiting."""
import itertools
import math

from ..primitives import rand
from ..spec import Action

_WORD = "waiting"
_PROMPT = "> "
_FULL = _WORD + "..."

_WIN = 5.0           # one decision tick: every 5 s it may speak
_CHANCE = 0.7        # ...with this probability
_BLINK = 1.0         # idle cursor on/off period (s) -- a lazy ~1 Hz
_CURW = 6            # cursor cell width (px), reserved so the blink doesn't shift the line

_DOT = 0.42          # dwell per dot-count while it "thinks"
_DOT_REPS = 2        # how many 1->2->3 dot pulses before erasing
_DEL = 0.05          # per-char backspace speed (s)

# humanized per-char type delays -> cumulative reveal schedule (uneven = natural)
_DELAYS = tuple(0.07 + 0.06 * (1.0 + math.sin(i * 1.7)) for i in range(len(_WORD)))
_CUM = tuple(itertools.accumulate(_DELAYS))
_TYPE_DUR = _CUM[-1]
_DOTS_DUR = _DOT_REPS * 3 * _DOT
_DEL_DUR = len(_FULL) * _DEL
_ACT_DUR = _TYPE_DUR + _DOTS_DUR + _DEL_DUR


def _pose(now):   # idle stare at the prompt, the odd lazy drift
    return math.sin(now * 0.4) * 2, 2 + math.sin(now * 0.6), 1.0


def _speaks(bucket):
    """Deterministic per-tick coin flip off the virtual clock -> True ~70% of ticks."""
    return rand(bucket + 1) < _CHANCE


def _script(now):
    """-> (text after the prompt, cursor mode): 'solid' typing, 'off' thinking, 'blink' idle."""
    if not _speaks(int(now / _WIN)):
        return "", "blink"
    t = now % _WIN
    if t >= _ACT_DUR:
        return "", "blink"                               # spoke already; back to idle blink
    if t < _TYPE_DUR:                                    # 1) peck the word out, char by char
        return _WORD[:sum(t >= c for c in _CUM)], "solid"
    t -= _TYPE_DUR
    if t < _DOTS_DUR:                                    # 2) pulse the dots while it waits
        return _WORD + "." * (int(t / _DOT) % 3 + 1), "off"
    t -= _DOTS_DUR
    return _FULL[:len(_FULL) - int(t / _DEL) - 1], "solid"  # 3) backspace it away


def _overlay(d, W, H, now, ox=0.0, oy=0.0):  # a centred ">_" that idly blinks, sometimes typing "waiting..."
    text, mode = _script(now)
    y = H - 11
    line = _PROMPT + text
    tw = d.textlength(line)
    x = round(W / 2 - (tw + _CURW) / 2)                  # centre prompt+text+cursor cell as one unit, always
    d.text((x, y - 1), line, fill=1)
    if mode == "solid" or (mode == "blink" and (now % _BLINK) < _BLINK / 2):
        d.rectangle([x + tw + 1, y + 8, x + tw + _CURW, y + 9], fill=1)  # '_' cursor, just past the text


ACTION = Action("waiting", mood="bored", pose=_pose, overlay=_overlay)
