"""EMP jolt -- an electromagnetic pulse frying the display. Arcs gather and crackle between the
eyes, a blinding flash discharges, the screen blacks out as a shockwave ring slams off-frame with
forked bolts and interference snow, then the panel reboots -- the eyes stuttering back through
rolling static, scanlines and torn rows before it settles. Plays ONCE (~1.6s), then self-ends to
natural eyes.

A vibe, not a reaction: a reaction has only `motion` (it could just scale the eyes). The arcs,
ring, static and tearing all need a full-screen `overlay`, which only the Action machinery has --
so `overlay` carries the detail, `pose` collapses then stutters the eyes back, `_done` self-ends."""
import math

from ..primitives import rand, smoothstep
from ..spec import Vibe

_CX, _CY = 64, 32
_LEYE, _REYE = 41, 87                              # eye centres (engine defaults)
_CHARGE, _FLASH, _DARK, _BOOT = 0.24, 0.10, 0.22, 1.04
_PERIOD = _CHARGE + _FLASH + _DARK + _BOOT         # ~1.6s, one-shot
_start = [0.0]                                     # this run's start clock (captured each frame by _done)


def _done(now, start):
    """Self-end after one ~1.6s pass; stash the start so the beats phase off elapsed time."""
    _start[0] = start
    return now - start >= _PERIOD


def _beat(now):
    """(name, 0..1 fraction) of the beat we're in, measured from this run's start."""
    t = now - _start[0]
    if t < _CHARGE:                          return "charge", t / _CHARGE
    if t < _CHARGE + _FLASH:                 return "flash", (t - _CHARGE) / _FLASH
    if t < _CHARGE + _FLASH + _DARK:         return "dark", (t - _CHARGE - _FLASH) / _DARK
    return "boot", (t - _CHARGE - _FLASH - _DARK) / _BOOT


def _eye_h(now):
    """Eye-height multiplier: tense -> collapsed at discharge -> stuttering back on reboot."""
    name, f = _beat(now)
    if name == "charge": return 1.0 + 0.12 * smoothstep(f)          # tense, widening
    if name == "flash":  return max(0.05, 1.0 - smoothstep(min(1.0, f / 0.6)))
    if name == "dark":   return 0.05                                # blanked
    boot = smoothstep(f)                                            # the steady recovery
    flick = 0.5 + 0.5 * abs(math.sin(f * math.pi * 6))            # strobe, frequent early
    return max(0.05, boot * (1.0 - (1.0 - flick) * (1.0 - boot)))   # flickers early, settles to 1.0


def _pose(now):
    name, _ = _beat(now)
    amp = 4.0 if name in ("charge", "dark") else (2.0 if name == "boot" else 0.0)
    n = int(now * 50)
    return (rand(n) - 0.5) * amp, (rand(n, 1) - 0.5) * amp, _eye_h(now)


# --------------------------------------------------------------- draw helpers
def _bolt(d, x0, y0, x1, y1, seg, seed):
    """A jagged lightning bolt (x0,y0)->(x1,y1), jitter easing out near the target."""
    px, py = x0, y0
    for s in range(1, seg + 1):
        f = s / seg
        bx = x0 + (x1 - x0) * f + (rand(seed, s) - 0.5) * 9 * (1 - f)
        by = y0 + (y1 - y0) * f + (rand(seed, s, 1) - 0.5) * 9 * (1 - f)
        d.line([px, py, bx, by], fill=1)
        px, py = bx, by


def _snow(d, n, seed):
    """Interference snow -- n random lit pixels."""
    for k in range(n):
        d.point((rand(seed, k) * 127, rand(seed, k, 1) * 63), fill=1)


def _ring(d, r, thick):
    """Concentric circle outlines (the EMP wavefront), drawn `thick` px wide."""
    for t in range(thick):
        rr = r - t
        if rr > 1:
            d.ellipse([_CX - rr, _CY - rr, _CX + rr, _CY + rr], outline=1)


# ------------------------------------------------------------------- beats
def _charge(d, f, now):
    """Build-up: forking arcs whip between the eyes, sparks rush into the gap, a core ignites."""
    seed = int(now * 30)
    for k in range(1 + int(f * 4)):                                # arcs jumping eye-to-eye via centre
        _bolt(d, _LEYE, _CY + (rand(seed, k) - 0.5) * 14,
              _REYE, _CY + (rand(seed, k, 9) - 0.5) * 14, 7, seed + k)
    for k in range(int(f * 10)):                                   # sparks drawn inward to the gap
        a, r = rand(seed, k, 3) * math.tau, 8 + (1 - f) * 24
        d.line([_CX + math.cos(a) * r, _CY + math.sin(a) * r,
                _CX + math.cos(a) * (r - 4), _CY + math.sin(a) * (r - 4)], fill=1)
    if f > 0.5:                                                    # a tight buzzing core forming
        d.ellipse([_CX - 3, _CY - 3, _CX + 3, _CY + 3], fill=1)


def _dark(d, f, now):
    """Dead panel: black screen, a shockwave ring racing off-frame, forked bolts, heavy snow."""
    d.rectangle([0, 0, 127, 63], fill=0)                          # erase the eyes -> dead screen
    e = smoothstep(f)
    _ring(d, int(6 + e * 120), 3)                                  # wavefront expanding off-frame
    _ring(d, int(6 + e * 72), 2)                                   # a second, trailing front
    seed = int(now * 26)
    for k in range(3):                                            # bolts forking out of dead centre
        a = rand(seed, k) * math.tau
        _bolt(d, _CX, _CY, _CX + math.cos(a) * 60, _CY + math.sin(a) * 34, 6, seed + k)
    _snow(d, 70, seed)


def _boot(d, f, now):
    """Reboot: snow thins, scanlines roll, rows tear and arcs crackle over the returning eyes."""
    res = 1.0 - smoothstep(f)                                      # how broken it still is
    seed = int(now * 24)
    if f < 0.10 and rand(seed) < 0.6:                             # a couple of black dropout frames early
        d.rectangle([0, 0, 127, 63], fill=0)
    _snow(d, int(60 * res), seed)
    for y in range(int(now * 90) % 6, 64, 6):                     # rolling CRT scanlines, drifting up
        if rand(seed, y) < 0.4 + 0.4 * res:
            d.line([0, y, 127, y], fill=0)
    for k in range(int(res * 4)):                                 # torn rows: a bright bar punched sideways
        y = int(rand(seed, k, 2) * 60)
        h = 1 + int(rand(seed, k, 5) * 3)
        d.rectangle([0, y, 127, y + h], fill=1)
        d.rectangle([0, y + h, 127, y + h + 1], fill=0)
    for k in range(int(res * 3)):                                 # arcs still crackling over an eye
        cx = _LEYE if rand(seed, k, 7) < 0.5 else _REYE
        _bolt(d, cx, 18, cx + (rand(seed, k) - 0.5) * 20, 46, 4, seed + k)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    name, f = _beat(now)
    if name == "charge":
        _charge(d, f, now)
    elif name == "flash":
        d.rectangle([0, 0, W - 1, H - 1], fill=1)                 # blinding discharge
    elif name == "dark":
        _dark(d, f, now)
    else:
        _boot(d, f, now)


VIBE = Vibe("emp_pulse", mood="alert", pose=_pose, overlay=_overlay, expired=_done, still=True)
