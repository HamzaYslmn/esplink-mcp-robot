"""Battery gauge -- a big horizontal cell along the BOTTOM showing the REAL charge, a charging bolt,
and a large % in the bottom-left. The eyes lift up to clear it, and emote the charge: focused while
charging, tired on battery.

Source priority: a bound ESP32 feed (GPIO34 through a divider, wired by the app when a board is
attached) > the host PC battery (stdlib, Windows) > PIP_BATTERY override > a demo sweep (headless
showcase). Charging draws a lightning bolt; a low cell blinks. The bound feed and PC read are
slow/blocking, so a daemon refreshes every few seconds while the overlay just paints the cache.
ponytail: LiPo curve is a flat 3.3-4.2V map -- tune it with the env knobs, real cells aren't linear."""
import ctypes
import math
import os
import threading

from PIL import ImageFont

_SEGS = 5

try:
    _FONT = ImageFont.load_default(size=17)      # big % in the bottom-left corner
except TypeError:                                # ancient Pillow
    _FONT = ImageFont.load_default()

# -- ESP32 feed (bound by the app when a board is attached) ----------------------------
_mv_src = None                                   # callable() -> calibrated pin millivolts (raises if link down)
_chg_src = None                                  # callable() -> charging bool, or None
_lock = threading.Lock()
_state = {"lvl": None, "chg": None, "at": -1.0, "busy": False}
_PERIOD = 5.0                                     # s between reads (battery moves slowly)


def bind(mv_fn, charge_fn=None):
    """Wire a real battery source. mv_fn() returns GPIO34's calibrated millivolts; charge_fn()
    returns True/False if a charge-status pin is wired. Called once by the app for a live board."""
    global _mv_src, _chg_src
    _mv_src, _chg_src = mv_fn, charge_fn


def _pc_battery():
    """Host battery via the OS (Windows GetSystemPowerStatus) -> (level 0..1|None, charging|None)."""
    try:
        class _S(ctypes.Structure):
            _fields_ = [("ac", ctypes.c_ubyte), ("flag", ctypes.c_ubyte),
                        ("pct", ctypes.c_ubyte), ("status", ctypes.c_ubyte),
                        ("life", ctypes.c_ulong), ("full", ctypes.c_ulong)]
        s = _S()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)):
            return None, None
        lvl = None if s.pct == 255 else s.pct / 100.0
        chg = None if s.ac == 255 else bool(s.ac)
        return lvl, chg
    except Exception:
        return None, None                        # not Windows / no battery


def _read():
    try:
        if _mv_src is not None:                   # real ESP32 cell on GPIO34
            mv = _mv_src() * float(os.getenv("PIP_BATTERY_DIVIDER", "2.0"))
            empty = float(os.getenv("PIP_BATTERY_EMPTY_MV", "3300"))
            full = float(os.getenv("PIP_BATTERY_FULL_MV", "4200"))
            lvl = max(0.0, min(1.0, (mv - empty) / (full - empty)))
            chg = _chg_src() if _chg_src else None
        else:
            lvl, chg = _pc_battery()
        with _lock:
            _state["lvl"], _state["chg"] = lvl, chg
    except Exception:
        with _lock:
            _state["lvl"] = None                  # link hiccup -> drop to fallback
    finally:
        with _lock:
            _state["busy"] = False


def _maybe_read(now):
    """Kick a non-blocking refresh if one is due (mirrors weather/ping_pong)."""
    with _lock:
        due = now - _state["at"] >= _PERIOD and not _state["busy"]
        if due:
            _state["busy"], _state["at"] = True, now
    if due:
        threading.Thread(target=_read, name="battery", daemon=True).start()


def _level(now):
    """Cached real reading, else PIP_BATTERY override, else a demo sweep. -> (level, charging)."""
    with _lock:
        lvl, chg = _state["lvl"], _state["chg"]
    if lvl is not None:
        return lvl, chg
    env = os.getenv("PIP_BATTERY")
    if env:
        try:
            return max(0.0, min(1.0, float(env) / 100.0)), None
        except ValueError:
            pass
    return 0.5 + 0.5 * math.sin(now * 0.2), None   # no source wired -> animated placeholder


def _bolt(d, cx, cy):
    """A lightning bolt centred at (cx,cy): an erased channel with a bright core, so it reads on
    filled or empty fill alike."""
    pts = [(cx + 3, cy - 6), (cx - 2, cy - 1), (cx + 2, cy - 1), (cx - 3, cy + 6)]
    d.line(pts, fill=0, width=4)                  # dark channel
    d.line(pts, fill=1, width=2)                  # bright bolt inside it


# big horizontal cell along the bottom; the eyes lift up (pose) to clear it. % rides bottom-left.
_BX, _BY, _BW, _BH = 42, 44, 80, 18           # body x42..122 (nub +3), y44..62 -- below the lifted eyes


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    _maybe_read(now)
    lvl, chg = _level(now)
    low = lvl <= 0.20 and not chg
    blink = low and int(now * 3) % 2              # low + unplugged -> blink the cell (not the %)
    if not blink:
        d.rectangle([_BX, _BY, _BX + _BW, _BY + _BH], outline=1)                    # body
        d.rectangle([_BX + _BW + 1, _BY + 5, _BX + _BW + 3, _BY + _BH - 5], fill=1) # + terminal nub
        seg = (_BW - 4) / _SEGS
        for i in range(round(lvl * _SEGS)):                                         # fills left-to-right
            sx = _BX + 2 + i * seg
            d.rectangle([sx, _BY + 2, sx + seg - 2, _BY + _BH - 2], fill=1)
        if chg:
            _bolt(d, _BX + _BW / 2, _BY + _BH / 2)
    pct = f"{round(lvl * 100)}%"                                                    # big % in the bottom-left
    d.text((1, H - 19), pct, font=_FONT, fill=1)


def _pose(now):
    """Lift the eyes up off the bottom gauge -- alert & high when charging, heavier/droopier on battery."""
    with _lock:
        chg = _state["chg"]
    if chg:
        return 0.0, -8.0 + math.sin(now * 1.5) * 0.5, 0.85    # charging: lifted, eyes open
    return 0.0, -6.0 + math.sin(now * 0.8) * 0.6, 0.55        # on battery: lower, squashed -> weary


class _Gauge:
    """Duck-typed Widget whose `mood` tracks the charge state -- the engine re-reads it each frame, so
    Pip looks focused while charging and tired on battery. (A frozen Widget can't carry a live mood.)"""
    name = "battery_gauge"
    pose, overlay = staticmethod(_pose), staticmethod(_overlay)
    expired = tic = None
    still = False

    @property
    def mood(self):
        if os.getenv("PIP_HUD_DIM"):
            return "standby"
        with _lock:
            chg, lvl = _state["chg"], _state["lvl"]
        if chg:
            return "happy" if lvl is not None and lvl >= 0.97 else "focused"   # full -> happy; topping up -> focused
        return "tired"                                                         # on battery -> weary


WIDGET = _Gauge()
