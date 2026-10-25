"""Hyperspace -- the jump to lightspeed, the way the films do it. Loops.

  cruise  -- a calm starfield drifting slowly outward from the vanishing point.
  stretch -- "punch it": every star stretches into a radial line. Its tail stays put while its
             head races out to infinity (head = tail / (1 - s), s -> 1: pure perspective), so the
             whole field turns into the iconic sunburst of streaks. Pip braces.
  flash   -- the jump.
  hyper   -- hyperspace / warp: streaks pour out of the centre and fly past, each one longer the
             closer it gets (perspective), the field gently twisting.
  drop    -- the streaks snap back into stars (the stretch in reverse) with a smaller flash, and
             Pip goes wide-eyed: we've arrived.
Stars are far away, so they only show on the dark panel -- they pass behind Pip's eyes.

Pip's face follows the ride, three beats only: open, friendly eyes gazing over the stars at
cruise, eyes wide with wonder as the stars stretch, a happy grin through hyperspace (a blink at
each flash, a faint judder), then back to friendly on arrival. The effect's `mood` is read every
frame, and the engine eases one eye shape into the next."""
import math
import random

import numpy as np

from ..primitives import frame

_W, _H = 128, 64
_VX, _VY = 64.0, 32.0                         # vanishing point
_SEQ = (("cruise", 2.6), ("stretch", 0.9), ("flash", 0.14), ("hyper", 4.0), ("drop", 0.5), ("arrive", 1.4))
_PERIOD = sum(d for _, d in _SEQ)
_N_STARS, _N_DASH = 46, 130
_s = {"t0": None, "last": None}


def _new_star(rng, near=False):
    a = rng.uniform(0, 2 * math.pi)
    r = rng.uniform(8, 26) if near else rng.uniform(4, 70)
    return [a, r, rng.random()]                              # angle, screen radius, twinkle phase


def _reset(now):
    rng = random.Random(int(now * 1000) & 0xFFFF)
    _s.update(t0=now, last=now, rng=rng, stars=[_new_star(rng) for _ in range(_N_STARS)],
              dash=[(2 * math.pi * (i + rng.random()) / _N_DASH, (i * 0.618 + rng.random() * 0.2) % 1.0,
                     rng.uniform(0.85, 1.15)) for i in range(_N_DASH)])   # even in angle and depth


def _phase(now):
    t = (now - _s["t0"]) % _PERIOD
    for name, dur in _SEQ:
        if t < dur:
            return name, t / dur
        t -= dur
    return "arrive", 1.0


def _pt(a, r):
    return _VX + r * math.cos(a), _VY + r * math.sin(a) * 0.62     # a little flatter: the wide panel


def _line(m, x0, y0, x1, y1):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    if n > 400:                                              # off to infinity: clip the length
        k = 400 / n
        x1, y1, n = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, 401
    xs = np.rint(np.linspace(x0, x1, n)).astype(int)
    ys = np.rint(np.linspace(y0, y1, n)).astype(int)
    ok = (xs >= 0) & (xs < _W) & (ys >= 0) & (ys < _H)
    m[ys[ok], xs[ok]] = True


def _starfield(m, dt, now, stretch):
    """Each star drifts out (cruise perspective); with `stretch` in (0, 1) it is drawn as a streak
    from its position to position / (1 - stretch)."""
    rng = _s["rng"]
    for st in _s["stars"]:
        a, r, tw = st
        st[1] = r * math.exp(0.09 * dt)                      # slow outward drift
        x, y = _pt(a, st[1])
        if not (-2 < x < _W + 2 and -2 < y < _H + 2):
            st[:] = _new_star(rng, near=True)
            continue
        if stretch > 0.01:
            hx, hy = _pt(a, st[1] / max(1e-3, 1 - stretch))
            _line(m, x, y, hx, hy)
        elif math.sin(now * 3 + tw * 40) > -0.6 or st[1] > 30:   # far, small stars twinkle
            _line(m, x, y, x, y)


def _hyper(m, now, amp):
    """Hyperspace: dashes born near the centre fly straight out; at depth z a dash sits at
    r = R0 / z and spans a fixed depth, so it lengthens as it nears -- the streaking tunnel."""
    for a, off, rate in _s["dash"]:
        z = 1.0 - ((now * 1.1 * rate + off) % 1.0)          # 1 far .. 0 here
        z0, z1 = max(z, 0.02), max(z - 0.05, 0.012)
        r0, r1 = 4.0 / z0, 4.0 / z1
        if r0 > 80 or r0 < 6:
            continue
        x0, y0 = _pt(a, r0)
        x1, y1 = _pt(a, min(r1, 160))
        if amp >= 1.0 or random.random() < amp:
            _line(m, x0, y0, x1, y1)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    if _s["t0"] is None or now < _s["last"] or now - _s["last"] > 0.5:
        _reset(now)
    dt = min(0.1, now - _s["last"])
    _s["last"] = now
    name, u = _phase(now)
    m = np.zeros((_H, _W), bool)
    if name in ("cruise", "arrive"):
        _starfield(m, dt, now, 0.0)
    elif name == "stretch":
        _starfield(m, dt, now, 0.97 * u ** 2.2)              # slow to start, then they shoot out
    elif name == "hyper":
        _hyper(m, now, min(1.0, u / 0.12))
    elif name == "drop":
        _starfield(m, dt, now, 0.97 * (1 - u) ** 1.6)        # the streaks snap back into stars
    img = frame(d)
    if img is None:
        return
    px = np.asarray(img, dtype=bool) | m                     # only the dark panel shows them
    if name == "flash" or (name == "drop" and u < 0.16):
        px = ~px
    img.frombytes(np.packbits(px, axis=1).tobytes())


_FACE = {"cruise": "neutral", "stretch": "awe", "flash": "awe",
         "hyper": "happy", "drop": "happy", "arrive": "neutral"}


def _pose(now):
    """A slow gaze over the stars at cruise, a blink at the flash, a faint judder in hyperspace."""
    if _s["t0"] is None:
        return 0.0, 0.0, 1.0
    name, _ = _phase(now)
    if name in ("cruise", "arrive"):
        return 5 * math.sin(now * 0.6), -1.5, 1.0
    if name == "flash":
        return 0.0, 0.0, 0.2
    if name == "hyper":
        return 0.4 * math.sin(now * 37), 0.3 * math.sin(now * 29), 1.0
    return 0.0, 0.0, 1.0


class _Warp:
    """A Vibe whose face follows the phase (the engine reads  every frame)."""
    name = "warp"
    pose = staticmethod(_pose)
    overlay = staticmethod(_overlay)
    expired = None
    still = False
    tic = None
    mood = property(lambda self: _FACE[_phase(_s["last"])[0]] if _s["t0"] is not None else "neutral")


VIBE = _Warp()
