"""Energy blast -- an anime power-up. The eyes pour their light into a glowing orb swelling in the
gap between them; streams of energy spiral in and accelerate, arcs crackle over its surface, then
at full charge they've vanished into it, a ring slams inward and the frame trembles -- and it
BOOMS: white flash, fireball, a bold starburst and thick shockwave bands, fading as the eyes ease
back. Plays ONCE (~7s), then self-ends to natural eyes.

Four eased beats -- charge, vibrate, boom, cool -- phased off elapsed time (captured by `_done`).
`pose` shrinks/locks the eyes; the overlay also carves their *width* out, so the orb never overlaps
a leftover eye bar."""
import math

from ..primitives import rand, smoothstep
from ..spec import Vibe

_CX, _CY = 64, 32                                  # orb sits in the gap between the eyes
_LEYE, _REYE = 41, 87                              # eye centres (engine defaults)
_CHARGE, _VIB, _BOOM, _COOL = 3.8, 0.9, 1.3, 1.4
_PERIOD = _CHARGE + _VIB + _BOOM + _COOL           # ~7.4s, one-shot
_ORB_MAX = 13
_start = [0.0]                                     # this run's start clock (captured each frame by _done)


def _done(now, start):
    """Self-end after one ~7s pass; also stash the start so the beats phase off elapsed time."""
    _start[0] = start
    return now - start >= _PERIOD


def _beat(now):
    """(name, 0..1 fraction) of the beat we're in, measured from this run's start."""
    t = now - _start[0]
    if t < _CHARGE:                       return "charge", t / _CHARGE
    if t < _CHARGE + _VIB:                return "vib", (t - _CHARGE) / _VIB
    if t < _CHARGE + _VIB + _BOOM:        return "boom", (t - _CHARGE - _VIB) / _BOOM
    return "cool", (t - _CHARGE - _VIB - _BOOM) / _COOL


def _ell(d, cx, cy, r, **kw):
    d.ellipse([cx - r, cy - r * 0.85, cx + r, cy + r * 0.85], **kw)   # squashed (perspective) circle


def _shake(now, amp):
    return (rand(int(now * 40)) - 0.5) * amp, (rand(int(now * 40), 1) - 0.5) * amp


def _eye_open(now):
    """Eye openness this frame: 1 = normal, 0 = fully poured into the orb (eased, never popping)."""
    name, f = _beat(now)
    if name == "charge":  return 1.0 - smoothstep(f)
    if name == "cool":    return smoothstep(f)
    return 0.0                                      # vib + boom: eyes are gone, the orb owns the face


def _pose(now):
    name, _ = _beat(now)
    jx, jy = _shake(now, 5) if name == "vib" else (0.0, 0.0)
    return jx, jy, max(0.05, _eye_open(now))       # locked on the orb, trembling at the peak


def _carve_eyes(d, now):
    """Erase the eyes' outer wings down to nothing as they pour in -- both height (pose) AND width
    (here) collapse, so the orb/aura never overlap a leftover eye bar."""
    keep = 18.0 * _eye_open(now)                    # visible half-width per eye -> 0 at full charge
    for cx in (_LEYE, _REYE):                       # ±22 margin covers the eyes even while they shake
        d.rectangle([cx - 22, 12, cx - keep, 52], fill=0)
        d.rectangle([cx + keep, 12, cx + 22, 52], fill=0)


def _bolt(d, x0, y0, x1, y1, seg, seed):
    """A jagged lightning bolt from (x0,y0) to (x1,y1), jitter easing out near the target."""
    px, py = x0, y0
    for s in range(1, seg + 1):
        f = s / seg
        bx = x0 + (x1 - x0) * f + (rand(seed, s) - 0.5) * 7 * (1 - f)
        by = y0 + (y1 - y0) * f + (rand(seed, s, 1) - 0.5) * 7 * (1 - f)
        d.line([px, py, bx, by], fill=1)
        px, py = bx, by


def _charge(d, cf, now, cx, cy):
    """The build: a swelling, flickering orb fed by accelerating spiral streams + surface arcs,
    haloed by radiating rings -- all intensifying with cf."""
    ease = smoothstep(cf)
    orb = 2 + ease * _ORB_MAX + math.sin(now * 9) * 1.2 * cf       # swelling core, flickering as it tightens
    seed = int(now * 18)

    streams = int(8 + cf * 22)                                     # denser inflow as it builds
    for i in range(streams):
        life = (now * (0.6 + cf * 1.3) + i / streams * 1.9) % 1.0
        r = orb + (1.0 - life) ** 1.6 * (52 - orb)                 # ease-in -> particle accelerates inward
        a = i * (math.tau / streams) + life * (2.0 + cf * 3.5) + now * (0.5 + cf)
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r * 0.85
        d.line([cx + math.cos(a + 0.16) * (r + 3),                 # short trailing tail -> motion
                cy + math.sin(a + 0.16) * (r + 3) * 0.85, x, y], fill=1)

    if cf > 0.12:                                                  # crackling feed drawn from each eye
        _bolt(d, _LEYE, _CY, cx - orb, cy, 5, seed)
        _bolt(d, _REYE, _CY, cx + orb, cy, 5, seed + 7)
    for k in range(int(cf * 5)):                                   # arcs crackling over the orb surface
        a = rand(seed, k) * math.tau
        _bolt(d, cx + math.cos(a) * orb, cy + math.sin(a) * orb * 0.85,
              cx + math.cos(a + 1.5) * (orb + 5), cy + math.sin(a + 1.5) * (orb + 5) * 0.85, 3, k + seed)

    _ell(d, cx, cy, orb, fill=1)                                   # the orb
    for k in range(1 + int(cf * 2)):                               # radiating aura rings, pulsing outward
        rr = orb + 4 + k * 4 + (math.sin(now * 6 - k) * 0.5 + 0.5) * 4
        _ell(d, cx, cy, rr, outline=1)


def _vib(d, vf, now):
    """Peak charge: full orb shaking, with a ring slamming inward -- the anticipation before the boom."""
    jx, jy = _shake(now, 5)
    _charge(d, 1.0, now, _CX + jx, _CY + jy)
    rr = (1.0 - vf) * 42 + _ORB_MAX                               # implosion ring collapsing onto the orb
    _ell(d, _CX + jx, _CY + jy, rr, outline=1)


def _boom(d, bf, now):
    if bf < 0.09:                                  # blinding flash
        d.rectangle([0, 0, 127, 63], fill=1)
        return
    e = 1.0 - (1.0 - bf) ** 2                      # ease-out: a hard snap that decelerates
    cx, cy = _CX, _CY

    core = max(0.0, (0.30 - bf) / 0.30) * 26       # a fireball that blooms then collapses inward
    if core > 1:
        _ell(d, cx, cy, core, fill=1)

    for k in range(2):                             # thick shockwave bands racing out (annulus = solid ring)
        ro = e * 130 - k * 18
        if ro > 6:
            _ell(d, cx, cy, ro, fill=1)
            _ell(d, cx, cy, ro - (6 - k * 2), fill=0)

    n, hub = 12, 7.0                               # bold solid starburst spikes off a bright hub (no spin)
    hw = (math.tau / n) * 0.5
    for i in range(n):
        a = i * (math.tau / n)
        tip = e * 82 * (1.0 if i % 2 == 0 else 0.62)
        d.polygon([(cx + math.cos(a - hw) * hub, cy + math.sin(a - hw) * hub * 0.85),
                   (cx + math.cos(a) * tip, cy + math.sin(a) * tip * 0.85),
                   (cx + math.cos(a + hw) * hub, cy + math.sin(a + hw) * hub * 0.85)], fill=1)
    hubr = hub * max(0.0, 1.0 - bf * 1.4)          # bright core hub the spikes spring from, fading out
    if hubr > 1:
        _ell(d, cx, cy, hubr, fill=1)

    for i in range(18):                            # flung sparks, drawn as short outward trails
        a, rr = rand(i) * math.tau, e * 74 * (0.55 + rand(i, 1) * 0.45)
        if rr > 8:
            d.line([cx + math.cos(a) * (rr - 6), cy + math.sin(a) * (rr - 6) * 0.85,
                    cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.85], fill=1)


def _cool(d, kf, now):
    fade = 1 - kf
    rr = 12 + kf * 22
    if rand(int(now * 10)) < fade:                 # dissipating ring, flickering out
        _ell(d, _CX, _CY, rr, outline=1)
    for i in range(8):                             # last embers drifting off
        if rand(i, int(now * 6)) < fade * 0.6:
            a, r2 = i * 0.785, 14 + kf * 30
            d.point((_CX + math.cos(a) * r2, _CY + math.sin(a) * r2 * 0.85), fill=1)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    name, f = _beat(now)
    _carve_eyes(d, now)                            # clear the eyes' footprint before any energy draws
    if name == "charge":
        _charge(d, f, now, _CX, _CY)
    elif name == "vib":
        _vib(d, f, now)
    elif name == "boom":
        _boom(d, f, now)
    else:
        _cool(d, f, now)


VIBE = Vibe("energy_blast", mood="focused", pose=_pose, overlay=_overlay, expired=_done, still=True)
