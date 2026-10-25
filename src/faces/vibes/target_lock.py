"""Target lock -- a one-eyed aim, special to this lock (the eye look is drawn here in the overlay,
not a registered mood). The left eye snaps shut to a line and the right sights down a focused
squint with a crosshair pupil; the corner brackets slam in to frame the face, and once locked the
pupil's centre blinks. No scanning, no expanding rings. One-shot intro then HOLDS -- no loop.
Trigger `target_release` to break lock."""
from ..primitives import smoothstep
from ..spec import Vibe

_LOCK = 0.55                                  # the converge-and-snap; past it the lock just HOLDS
_L, _T, _R, _B = 19, 10, 109, 53             # lock-box frame -- a margin OUTSIDE the eyes
_AX, _AY = 87, 32                             # the aiming (right) eye centre -- where the sight sits
_AR, _CUT = 13, 10                             # round aiming eye, top trimmed flat by _CUT = a focused lid
_state = {"start": None, "last": -1.0}        # a >0.5s gap means a fresh lock-on


def _elapsed(now):
    """Seconds since this lock-on began (a gap restarts the clock)."""
    s = _state
    if s["start"] is None or now - s["last"] > 0.5 or now < s["last"]:
        s["start"] = now
    s["last"] = now
    return now - s["start"]


def _over(s):                                 # ease-out with a little overshoot -> a snappy slam
    s -= 1
    return 1 + 2.7 * s ** 3 + 1.7 * s ** 2


def _aim_eyes(d):                             # special to the lock: shut the left eye, round focused right
    d.rectangle([21, 12, 61, 31], fill=0)     # LEFT eye -> covered down to a thin closed line
    d.rectangle([21, 34, 61, 52], fill=0)
    d.rectangle([66, 11, 108, 53], fill=0)    # wipe the engine's right eye...
    d.ellipse([_AX - _AR, _AY - _AR, _AX + _AR, _AY + _AR], fill=1)   # ...redraw it round...
    d.rectangle([_AX - _AR - 1, 11, _AX + _AR + 1, _AY - _CUT], fill=0)   # ...then trim the top flat = focused


def _pupil(d, arm, gap=2, center=False):      # a bold crosshair carved (black) into the white aiming eye
    w = 2
    d.line([_AX - gap - arm, _AY, _AX - gap, _AY], fill=0, width=w)
    d.line([_AX + gap, _AY, _AX + gap + arm, _AY], fill=0, width=w)
    d.line([_AX, _AY - gap - arm, _AX, _AY - gap], fill=0, width=w)
    d.line([_AX, _AY + gap, _AX, _AY + gap + arm], fill=0, width=w)
    if center:
        d.ellipse([_AX - 2, _AY - 2, _AX + 2, _AY + 2], fill=0)


def _corners(d, f, n=8):                      # L-brackets lerp from screen corners (f=0) onto the frame (f=1)
    lerp = lambda a, b: a + (b - a) * f
    for ex, ey, bx, by, sx, sy in (
            (1, 1, _L, _T, 1, 1), (126, 1, _R, _T, -1, 1),
            (1, 62, _L, _B, 1, -1), (126, 62, _R, _B, -1, -1)):
        x, y = lerp(ex, bx), lerp(ey, by)
        d.line([x, y, x + n * sx, y], fill=1)
        d.line([x, y, x, y + n * sy], fill=1)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    t = _elapsed(now)
    _aim_eyes(d)                                            # the one-eyed aim face, every frame
    if t < _LOCK:                                           # LOCK: brackets slam in, pupil crosshair tightens
        s = smoothstep(t / _LOCK)
        _corners(d, _over(s))
        _pupil(d, int(9 - 5 * s))
    else:                                                   # HOLD: locked, the pupil's centre blinks
        if t - _LOCK < 0.16:                                # a single confirm flash -- no rings
            d.rectangle([_L, _T, _R, _B], outline=1)
        _corners(d, 1.0)
        _pupil(d, 4, center=int(now * 3) % 2 == 0)          # locked feeling -> centre blinks


VIBE = Vibe("target_lock", mood="neutral", overlay=_overlay, still=True)
