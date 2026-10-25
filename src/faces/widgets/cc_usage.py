"""Claude Code usage HUD -- the Claude Code buddy on the left (the character, not Pip's eyes) and
two gauges on the right: the rolling 5-hour and weekly plan caps, each with a % and a reset
countdown. The buddy bobs calmly with headroom and shivers + sweats as a cap fills.

Accurate source: these are Anthropic's real numbers (same as `/usage`), not a guess. Claude Code
only exposes them to a **statusline** command, so `.claude/hooks/cc_usage_statusline.py` captures
`rate_limits` to a small JSON file each turn and this widget reads it. No statusline / not on
Pro-Max -> the gauges read "waiting" until data lands. The file is tiny, so we just stat+read it
(no daemon thread); the reset countdown is recomputed from the stored epoch every frame.

Owning the whole screen: a widget overlay draws AFTER the eyes, so this one clears the buffer first
and paints its own scene -- no eyes, no extra mood, fully self-contained."""
import json
import math
import os
import time
from pathlib import Path

from PIL import ImageFont

_FILE = Path.home() / ".claude" / "cc_usage.json"        # statusline hook writes here, we read it
_PERIOD = 2.0                                             # s between file re-reads

try:
    _F = ImageFont.load_default(size=12)                 # labels + %
    _FS = ImageFont.load_default(size=9)                 # tiny reset countdown
except TypeError:                                        # ancient Pillow
    _F = _FS = ImageFont.load_default()

# only the engine thread touches these -> no lock needed
_state = {"p5": None, "pw": None, "r5_at": 0.0, "rw_at": 0.0, "mtime": -1.0, "at": -1e9}


def _read():
    """Reload the statusline-written file if it changed. Percentages are 0..1, resets are epoch s."""
    try:
        st = _FILE.stat()
        if st.st_mtime == _state["mtime"]:
            return
        d = json.loads(_FILE.read_text())
    except Exception:
        return                                           # missing / half-written -> keep last good
    _state["mtime"] = st.st_mtime
    fh, wk = d.get("five_hour") or {}, d.get("seven_day") or {}
    p5, pw = fh.get("used_percentage"), wk.get("used_percentage")
    _state["p5"] = None if p5 is None else min(1.0, p5 / 100.0)
    _state["pw"] = None if pw is None else min(1.0, pw / 100.0)
    _state["r5_at"] = fh.get("resets_at") or 0.0
    _state["rw_at"] = wk.get("resets_at") or 0.0


def _maybe_read(now):
    if now - _state["at"] >= _PERIOD:
        _state["at"] = now
        _read()


def _fmt(secs):
    """Compact reset countdown: '2d 3h' / '4h 12m' / '7m'."""
    d, h, m = int(secs // 86400), int(secs % 86400 // 3600), int(secs % 3600 // 60)
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


# The Claude Code buddy -- outline straight from claudecode.svg (viewBox 24x24, y shifted up 5 so
# it starts at 0). Drawn as one filled polygon with the two eyes carved out.
_LOGO = [(20.998, 5.949), (24, 5.949), (24, 9.051), (21, 9.051), (21, 12.079), (19.513, 12.079),
         (19.513, 15), (18, 15), (18, 12.079), (16.513, 12.079), (16.513, 15), (15, 15),
         (15, 12.079), (9, 12.079), (9, 15), (7.488, 15), (7.488, 12.079), (6, 12.079), (6, 15),
         (4.487, 15), (4.487, 12.079), (3, 12.079), (3, 9.05), (0, 9.05), (0, 5.95), (3, 5.95),
         (3, 0), (20.998, 0)]
_EYES = [(6, 3.102, 7.488, 5.949), (16.51, 3.102, 18, 5.949)]   # carved holes (x0,y0,x1,y1)


def _buddy(d, ox, oy, s, t, stress):
    """Draw the Claude Code buddy scaled by `s` at origin (ox,oy). `t` bobs it + blinks; `stress`
    0..1 makes it blink fast, jitter, and sweat as a cap fills."""
    oy += math.sin(t * 2.0) * 1.5                           # gentle idle bob
    ox += (int(t * 12) % 2) if stress >= 0.9 else 0         # nervous shiver when nearly capped
    d.polygon([(ox + x * s, oy + y * s) for x, y in _LOGO], fill=1)
    blink = math.sin(t * 0.8) > 0.97 or (stress >= 0.9 and int(t * 6) % 2 == 0)
    for x0, y0, x1, y1 in _EYES:                            # eyes: carved open, filled shut on a blink
        d.rectangle([ox + x0 * s, oy + y0 * s, ox + x1 * s, oy + y1 * s], fill=1 if blink else 0)
    if stress >= 0.9:                                       # sweat bead off the top-right
        bx, by = ox + 23 * s, oy + 1
        d.ellipse([bx, by, bx + 4, by + 5], outline=1)


def _gauge(d, x, y, w, label, pct, reset):
    """A labelled gauge: 'label .... NN%' over a rounded track + fill, reset countdown below.
    pct None -> no data yet, shows '--' and 'waiting'."""
    d.text((x, y), label, font=_F, fill=1)
    ps = "--" if pct is None else f"{round(pct * 100)}%"
    d.text((x + w - d.textlength(ps, font=_F), y), ps, font=_F, fill=1)
    by = y + 13
    d.rounded_rectangle([x, by, x + w, by + 6], radius=3, outline=1)
    if pct:
        fw = x + 1 + (w - 2) * pct
        if fw > x + 1:
            d.rounded_rectangle([x, by, fw, by + 6], radius=3, fill=1)
    sub = f"resets {_fmt(reset)}" if (pct is not None and reset) else "waiting"
    d.text((x, by + 8), sub, font=_FS, fill=1)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    _maybe_read(now)
    p5, pw = _state["p5"], _state["pw"]
    wall = time.time()
    r5 = max(0.0, _state["r5_at"] - wall) if _state["r5_at"] else 0.0
    rw = max(0.0, _state["rw_at"] - wall) if _state["rw_at"] else 0.0
    d.rectangle([0, 0, W - 1, H - 1], fill=0)             # own the whole screen (drawn after the eyes)
    s = 2.0                                                # logo is 24 wide -> ~48px, fits the left half
    _buddy(d, 1, (H - 15 * s) / 2, s, now, max(p5 or 0.0, pw or 0.0))   # buddy mirrors the fuller cap
    px, pw_ = 52, W - 52 - 2                              # right panel: x52..W-2
    _gauge(d, px, 2, pw_, "5H", p5, r5)
    _gauge(d, px, 34, pw_, "WK", pw, rw)


class _Usage:
    """Duck-typed Widget owning the full screen; mood only sets panel brightness (eyes are erased)."""
    name = "cc_usage"
    pose = None
    overlay = staticmethod(_overlay)
    expired = tic = None
    still = False
    mood = property(lambda self: "standby" if os.getenv("PIP_HUD_DIM") else "neutral")


WIDGET = _Usage()
