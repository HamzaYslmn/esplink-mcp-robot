"""Ping/pong as a sonar exchange -- a request/response round-trip, not a bouncing ball.

A PING sonar pulses slowly out from the TOP-LEFT corner (the PC) with "PING" in the top-right;
after a beat a PONG pulses back from the BOTTOM-RIGHT corner (the ESP32) with "PONG <ms>" in the
bottom-left. Each pulse is two close wavefronts trailed by one distant ring, plus a pulsing
contact blip. The eyes are kept small (so the labels read) and glance toward the live corner.

When a board is connected the app calls `bind()` with a real latency source, so the PONG reads the
measured round-trip ("PONG 25ms"); with no board it stays a plain animated handshake."""
import math
import threading

from PIL import ImageFont

from ..primitives import smoothstep
from ..spec import Action

try:
    _FONT = ImageFont.load_default(size=10)
except TypeError:                             # ancient Pillow
    _FONT = ImageFont.load_default()

# timeline (s): a pulse expands (_OUT), then a quiet beat (_HOLD); ping segment, then pong segment
_OUT, _HOLD = 1.3, 0.6
_SEG = _OUT + _HOLD
_CYCLE = 2 * _SEG

_MAXR = 150               # wavefront sweeps past the far corner (diagonal ~143px)
_HMULT = 0.6              # squash the borrowed eyes shorter still -> room for the labels

# -- real latency, measured off the live link when a board is connected --
_PERIOD = 1.0                                 # s between round-trip measurements
_src = None                                   # callable() -> round-trip seconds (raises if link down)
_lock = threading.Lock()
_state = {"ms": None, "at": -1.0, "busy": False}


def bind(ping_fn):
    """Wire a real latency source: ping_fn() returns the round-trip time in seconds (raises if the
    link is down). Called once by the app when an ESP32 is connected; left unbound otherwise."""
    global _src
    _src = ping_fn


def _measure():
    try:
        rtt = _src()
        with _lock:
            _state["ms"] = max(0, round(rtt * 1000))
    except Exception:
        with _lock:
            _state["ms"] = None               # link hiccup -> drop the number, fall back to plain
    finally:
        with _lock:
            _state["busy"] = False


def _maybe_measure(now):
    """Kick a non-blocking round-trip if one is due (mirrors weather's background fetch)."""
    if _src is None:
        return
    with _lock:
        if now - _state["at"] >= _PERIOD and not _state["busy"]:
            _state["busy"], _state["at"] = True, now
            threading.Thread(target=_measure, name="ping_pong", daemon=True).start()


def _pong_label():
    with _lock:
        ms = _state["ms"]
    return "PONG" if ms is None else f"PONG - {ms}ms"


def _sonar(d, cx, cy, a0, a1, prog):
    """A slow sonar pulse from a corner: two close wavefronts trailed by one distant ring."""
    lead = smoothstep(prog) * _MAXR
    for off, w in ((0, 2), (11, 2), (50, 1)):                  # two close waves + one distant
        r = lead - off
        if r > 2:
            d.arc([cx - r, cy - r, cx + r, cy + r], a0, a1, fill=1, width=w)


def _contact(d, x, y, now):
    """A pulsing blip -- the node at the far corner being pinged."""
    s = 1.5 + (math.sin(now * 6) * 0.5 + 0.5) * 2
    d.ellipse([x - s, y - s, x + s, y + s], fill=1)


def _pose(now):
    """Small eyes, glancing toward the transmitting corner -- up-left on ping, down-right on pong."""
    return (-6.0, -4.0, _HMULT) if (now % _CYCLE) < _SEG else (6.0, 4.0, _HMULT)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    _maybe_measure(now)
    t = now % _CYCLE
    if t < _SEG:                                               # PING segment: top-left -> top-right
        d.text((W - d.textlength("PING", font=_FONT) - 9, 2), "PING", font=_FONT, fill=1)
        _contact(d, W - 4, 6, now)
        if t < _OUT:
            _sonar(d, 0, 0, 0, 90, t / _OUT)
    else:                                                      # PONG segment: bottom-right -> bottom-left
        d.text((9, H - 12), _pong_label(), font=_FONT, fill=1)
        _contact(d, 4, H - 7, now)
        local = t - _SEG
        if local < _OUT:
            _sonar(d, W - 1, H - 1, 180, 270, local / _OUT)


ACTION = Action("ping_pong", mood="scared", pose=_pose, overlay=_overlay)   # 'scared' = small, plain eyes
