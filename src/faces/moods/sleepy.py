"""Drowsy, fighting sleep: the eyes sit half-lidded in a squint, wander around like the idle gaze and
blink now and then. After a 5s look-around pause there's a 50% chance Pip nods off -- it stops where
it's looking, the lids narrow shut to a centred 1px slit and hold dead still while a growing 'z z Z'
puffs up, then it shudders awake, opens a little, and eases back down to the squint and looks around
again. (Lighter than `snore`, which is real, heaving sleep.) The 5s pause guarantees a look-around
between naps; it falls asleep mid-glance, not recentred, and doesn't drift once asleep.

Drawn `bare`: the decor owns the whole face so it can wander, blink, narrow to a slit, freeze and
shudder -- none of which a held mood's static lids could do. Stateless: the dice, glances, blinks and
frozen anchor are all hashed off the clock -> replays exactly."""
import math

from PIL import ImageFont

from ..primitives import rand, rounded_rect, smoothstep
from ..spec import Mood

# ponytail: eye geometry mirrors the engine defaults (eye_w=36, gap=10, 128x64) -- update if those change
_CXL, _CXR, _CY = 41, 87, 32          # eye centres
_EYE_W = 34                           # eye width
_SLEEP, _SQUINT, _WAKE = 1.0, 11.0, 18.0   # lid height: asleep slit / half-lidded squint / startle-open

_LOOK = 5.0                                       # guaranteed look-around before each nap dice
_CLOSE, _HOLD, _SHUDDER, _SETTLE = 0.9, 1.4, 0.35, 0.9   # nap beats: shut / hold+Z / startle / ease back
_PERIOD = _LOOK + _CLOSE + _HOLD + _SHUDDER + _SETTLE   # 8.55s -> a nap is always >=5s after the last
_GLANCE = 2.2                                     # s between idle glance targets

try:
    _ZF = [ImageFont.load_default(size=s) for s in (10, 13, 17)]   # growing z z Z
except TypeError:                                                  # ancient Pillow
    _ZF = [ImageFont.load_default()] * 3


def _mix(a, b, e):
    return a + (b - a) * e


def _gaze(now):
    """Idle-style glances: dart to a fresh random spot each window, hold, ~30% of them centred."""
    def tgt(n):
        return (0.0, 0.0) if rand(n, 7) < 0.3 else ((rand(n) * 2 - 1) * 15, (rand(n, 1) * 2 - 1) * 6)
    g = now / _GLANCE
    i = int(g)
    (x0, y0), (x1, y1) = tgt(i), tgt(i + 1)
    e = smoothstep(min(1.0, (g - i) / 0.35))         # quick dart in the first third, then hold
    return _mix(x0, x1, e), _mix(y0, y1, e)


def _blink(now):
    """A quick involuntary blink at the start of ~40% of glances (eyes blink as they dart)."""
    g = now / _GLANCE
    f = g - int(g)
    if f > 0.18 or rand(int(g), 3) > 0.4:
        return 0.0
    return math.sin(f / 0.18 * math.pi)              # 0 -> 1 -> 0 over ~0.4s


def _state(now):
    """(visible height px, x, y, zzz 0..1 or None) for this instant -- the whole timeline in one place."""
    ws = (now // _PERIOD) * _PERIOD                  # this period's start (for the frozen anchor)
    t = now - ws
    lx, ly = _gaze(now)
    bob = math.sin(now * 1.7)                        # gentle breathing
    if t < _LOOK or rand(int(now // _PERIOD)) >= 0.5:   # awake: squint, blink, look around
        return _mix(_SQUINT, _SLEEP, _blink(now)), lx, ly + bob, None
    ax, ay = _gaze(ws + _LOOK)                        # where it was looking when it nodded off -> frozen
    t -= _LOOK
    if t < _CLOSE:                                    # nod off in place: squint -> slit, breathing fades out
        e = smoothstep(t / _CLOSE)
        return _mix(_SQUINT, _SLEEP, e), ax, ay + bob * (1 - e), None
    t -= _CLOSE
    if t < _HOLD:                                     # asleep: dead-still crescent + one growing 'z z Z'
        return _SLEEP, ax, ay, t / _HOLD
    t -= _HOLD
    if t < _SHUDDER:                                  # shudder awake in place: slit -> open + jitter
        f = t / _SHUDDER
        tr = 1.0 - f
        return _mix(_SLEEP, _WAKE, smoothstep(min(1.0, f / 0.5))), \
            ax + tr * 3.0 * math.sin(now * 75), ay + tr * 1.5 * math.sin(now * 90 + 1.0), None
    e = smoothstep((t - _SHUDDER) / _SETTLE)          # settle: open -> squint, gaze + breath resume
    return _mix(_WAKE, _SQUINT, e), _mix(ax, lx, e), _mix(ay, ly + bob, e), None


def _eye(d, cx, cy, h):
    """A centred rounded slit `h` px tall -- narrows to a visible 1px line when asleep."""
    rounded_rect(d, cx - _EYE_W / 2, cy - h / 2, _EYE_W, h, min(_EYE_W, h) * 12 / 36, 1)


def _zs(d, p, ox):
    """One growing 'z z Z' puffing up-right of the eyes, the letters appearing and rising in turn."""
    for i, f in enumerate(_ZF):
        a = p * 3 - i
        if a >= 0:
            d.text((_CXR + ox + 12 + i * 5, _CY - 6 - i * 6 - min(1.0, a) * 6), "Z", font=f, fill=1)


def _decor(d, W, H, now, ox=0.0, oy=0.0):
    vis, cx, cy, z = _state(now)
    _eye(d, _CXL + ox + cx, _CY + oy + cy, vis)
    _eye(d, _CXR + ox + cx, _CY + oy + cy, vis)
    if z is not None:
        _zs(d, z, cx)


MOOD = Mood("sleepy", bare=True, still=True, decor=_decor)
