"""Rain on the window -- Pip gazes out through a wet pane. A small stochastic physics sim, seeded
fresh on every activation, so no two showers look alike. One set of rules, followed throughout:

- Weather: wind is mean-reverting noise plus random gusts (quick build, slow die-off); the
  shower's intensity wanders the same way and swells with each gust.
- Rain: every drop is a particle with a depth. Near drops fall faster and blur into longer streaks;
  far ones are short and dotted. Wind carries them with inertia, so a streak's slant is its real
  velocity. Most miss the pane and splash on the sill (ballistic droplets); a few near ones hit the
  glass -- they thicken as they close in, then splat into a bead and a crown of tiny droplets.
- Glass: beads come only from impacts and grow only by merging. Surface tension holds a bead until
  its weight beats it; then gravity wins against drag. Runners sweep up beads in their path
  (heavier -> faster), catch on specks of dirt, get nudged by the wind, and prefer the wet tracks
  earlier runners left, so rivulets form and get reused. Beads evaporate by the d^2 law (area
  shrinks steadily), so specks vanish in a blink and a stalled bead clears in a few seconds.
- Sill: runners pour into a thin film of water along the bottom. The sill tilts a little (a random
  side each run): the film spreads, flows downhill -- ripples show which way -- and drains off the
  edge, so it never just piles up.
- A storm: lightning at random intervals, a random-walk bolt, one or two flashes.

Kept sparse on purpose: on a 1-bit panel every extra speck reads as another drop. Everything is
XOR-ed in through one numpy mask, so water over a lit eye shows dark -- you're looking through the
glass. Self-check: `cd src && uv run python -m faces.vibes.rain_window`."""
import math
import random

import numpy as np

from ..primitives import frame
from ..spec import Vibe

_W, _H = 128, 64
_G_GLASS, _DRAG = 180.0, 6.0                      # px/s^2 gravity on the glass, 1/s viscous drag
_G_AIR = 300.0                                    # px/s^2 for splash droplets in flight
_R_PIN = 1.8                                      # surface tension holds a bead smaller than this
_EVAP = 0.8                                       # px^2/s of area every bead loses (d^2 law): a stalled 1.8 px bead ~4 s
_RAIN_RATE = 20.0                                 # drops/s at full intensity
_HIT_P = 0.25                                     # chance a near drop hits the pane
_MAX = 40                                         # beads on the pane at once
_SILL_FLOW, _SILL_SPREAD = (6.0, 12.0), 18.0      # px/s downhill flow range, px^2/s spreading

_SEED = None                                      # None = fresh randomness every activation (tests pin it)
_rng = random.Random()
_s = {}                                           # sim state; reset on a fresh activation


def _reset(now):
    seed = _rng.randrange(2 ** 32) if _SEED is None else _SEED
    _rng.seed(seed)
    _s.update(last=now, wind=_rng.uniform(0.05, 0.4), gust=0.0, gust_v=0.0, rain=_rng.uniform(0.35, 0.75),
              drops=[], splash=[], flying=[], beads=[], wet=np.zeros((_H, _W)),
              dirt=np.random.default_rng(seed).random((_H, _W)) < 0.025,   # this pane's specks of dirt
              sill=np.zeros(_W), tilt=_rng.choice((-1, 1)) * _rng.uniform(*_SILL_FLOW), ripple=0.0,
              bolt=None, next_bolt=now + _rng.uniform(5, 14), stats={"splat": 0, "sill": 0, "run": 0})
    for _ in range(_rng.randint(6, 10)):          # it's been raining: a few recent impacts on the glass
        _s["beads"].append(_bead(_rng.uniform(2, _W - 3), _rng.uniform(2, _H - 8), _impact_size()))


def _bead(x, y, r):
    return {"x": x, "y": y, "r": r, "vy": 0.0, "pin": 0.0, "trail": 0.0}


def _impact_size():
    return 0.9 + 1.5 * _rng.random() ** 2.5        # mostly small; now and then one heavy enough to run at once


def _weather(dt):
    """Ornstein-Uhlenbeck wind + rain intensity, with Poisson gusts layered on top."""
    s, n = _s, math.sqrt(dt)
    s["wind"] += 0.5 * (0.22 - s["wind"]) * dt + 0.12 * n * _rng.gauss(0, 1)
    s["rain"] += 0.15 * (0.55 - s["rain"]) * dt + 0.15 * n * _rng.gauss(0, 1)
    s["rain"] = min(1.0, max(0.15, s["rain"]))
    if _rng.random() < dt / 9.0:                  # a gust arrives
        s["gust_v"] = _rng.uniform(0.25, 0.6)
    s["gust"] += (s["gust_v"] - s["gust"]) * min(1.0, dt / 0.6)   # builds fast...
    s["gust_v"] *= math.exp(-dt / 2.5)            # ...dies off slowly
    return min(1.0, max(-0.1, s["wind"] + s["gust"])), min(1.0, s["rain"] + 0.3 * s["gust"])


def _step_air(dt, wind, rain):
    s = _s
    for _ in range(int(dt * _RAIN_RATE * rain) + (_rng.random() < (dt * _RAIN_RATE * rain) % 1)):
        z = _rng.random()                         # depth: 0 far .. 1 near
        vy = (45 + 75 * z) * _rng.uniform(0.9, 1.1)
        hit = z > 0.7 and _rng.random() < _HIT_P
        s["drops"].append({"x": _rng.uniform(-wind * _H, _W + 2), "y": -6.0, "z": z, "vx": wind * vy, "vy": vy,
                           "hit_y": _rng.uniform(3, _H - 12) if hit else None})
    keep = []
    for d in s["drops"]:
        d["vx"] += (wind * d["vy"] - d["vx"]) * min(1.0, dt / (0.12 + 0.1 * d["z"]))   # wind, with inertia
        d["x"] += d["vx"] * dt
        d["y"] += d["vy"] * dt
        if d["hit_y"] is not None and d["y"] >= d["hit_y"]:
            _splat(d["x"], d["y"], wind)
        elif d["y"] >= _H - 1:                    # misses the pane: splashes on the sill
            s["stats"]["sill"] += 1
            for _ in range(_rng.randint(1, 2)):
                s["splash"].append({"x": d["x"], "y": _H - 1.0, "vx": _rng.uniform(-30, 30) + wind * 25,
                                    "vy": -_rng.uniform(15, 40) * (0.5 + d["z"])})
        else:
            keep.append(d)
    s["drops"] = keep
    for p in s["splash"]:                          # ballistic splash droplets
        p["vy"] += _G_AIR * dt
        p["x"] += p["vx"] * dt
        p["y"] += p["vy"] * dt
    s["splash"] = [p for p in s["splash"] if p["y"] < _H]
    for f in s["flying"]:                          # crown droplets skid across the glass and stick
        f["t"] -= dt
        f["vx"] *= math.exp(-14 * dt)
        f["vy"] = f["vy"] * math.exp(-14 * dt) + _G_GLASS * 0.3 * dt
        f["x"] += f["vx"] * dt
        f["y"] += f["vy"] * dt
        if f["t"] <= 0:
            s["beads"].append(_bead(f["x"], f["y"], _rng.uniform(0.5, 0.8)))
    s["flying"] = [f for f in s["flying"] if f["t"] > 0]


def _splat(x, y, wind):
    """A drop hits the glass: a bead where it landed, a crown of tiny droplets thrown out radially."""
    _s["beads"].append(_bead(x, y, _impact_size()))
    _s["stats"]["splat"] += 1
    for _ in range(_rng.randint(1, 3)):
        a, sp = _rng.uniform(0, 2 * math.pi), _rng.uniform(25, 55)
        _s["flying"].append({"x": x, "y": y, "vx": math.cos(a) * sp + wind * 20, "vy": math.sin(a) * sp,
                             "t": _rng.uniform(0.08, 0.16)})


def _wet_at(x, y):
    xi, yi = int(x), int(y)
    return _s["wet"][yi, xi] if 0 <= xi < _W and 0 <= yi < _H else 0.0


def _step_glass(dt, wind):
    s = _s
    s["wet"] *= math.exp(-dt / 20.0)              # old tracks dry over ~20 s
    for b in s["beads"]:
        b["r"] = math.sqrt(max(0.0, b["r"] ** 2 - _EVAP * dt))   # every bead evaporates: small ones go first
        if b["r"] < _R_PIN or b["pin"] > 0:       # still: held by surface tension (or caught on dirt)
            b["pin"] = max(0.0, b["pin"] - dt)
            b["vy"] = 0.0
            continue
        a = _G_GLASS * (1 - (_R_PIN / b["r"]) ** 2) - _DRAG * b["vy"]   # weight past surface tension, minus drag
        b["vy"] = max(0.0, b["vy"] + a * dt)
        dy = b["vy"] * dt
        if dy > 0.3:
            s["stats"]["run"] += 1
        xi, yi = int(b["x"]), int(b["y"])
        on_track = _wet_at(b["x"], b["y"] + 2) > 0.3
        if not on_track and 0 <= xi < _W and 0 <= yi < _H and s["dirt"][yi, xi] and _rng.random() < 0.6:
            b["pin"] = _rng.uniform(0.1, 0.6)     # a speck of dirt; wet tracks are slick, so they skip this
        best = max((-1, 0, 1), key=lambda k: _wet_at(b["x"] + k, b["y"] + 2) + _rng.random() * 0.15)
        b["x"] += best * 0.6 * dy + _rng.gauss(0, 0.25) * dy + wind * dt * 2.5   # follow the wet, wobble, wind
        b["y"] += dy
        for k in (-1, 0, 1):                      # leave a wet track behind
            xk, yk = int(b["x"]) + k, int(b["y"])
            if 0 <= xk < _W and 0 <= yk < _H:
                s["wet"][yk, xk] = 1.0
        b["trail"] += dy
        if b["trail"] > 2.5 and _rng.random() < 0.7:   # sheds a tiny bead behind it, losing a little mass
            b["trail"], b["r"] = 0.0, math.sqrt(max(0.0, b["r"] ** 2 - 0.25))
            s["beads"].append(_bead(b["x"], b["y"] - b["r"] - 1.2, 0.75))   # a short-lived trail dot
        if b["y"] > _H - 3:                       # pours into the sill's film
            xi = int(b["x"])
            s["sill"][max(0, xi - 3):xi + 4] += b["r"] ** 2 * 0.15
            b["r"] = 0.0
    live = sorted((b for b in s["beads"] if b["r"] >= 0.4 and -2 < b["x"] < _W + 1), key=lambda b: -b["r"])
    merged = []
    for b in live:                                # touching beads coalesce: areas add, a runner keeps going
        for q in merged:
            if (b["x"] - q["x"]) ** 2 + (b["y"] - q["y"]) ** 2 < (b["r"] + q["r"]) ** 2:
                q["r"], q["vy"] = math.hypot(q["r"], b["r"]), max(q["vy"], b["vy"])
                break
        else:
            merged.append(b)
    s["beads"] = merged[:_MAX]


def _step_sill(dt):
    """The film on the sill: spreads (diffusion), flows downhill (upwind advection), drains off the
    low edge, and slowly evaporates. Sub-stepped so it stays stable at any frame rate."""
    s = _s
    c, h = s["tilt"], s["sill"]
    n = max(1, math.ceil(max(abs(c) * dt / 0.5, _SILL_SPREAD * dt / 0.4)))
    k = dt / n
    for _ in range(n):
        pad = np.concatenate(([0.0], h, [0.0]))   # open ends: water reaching an edge leaves the screen
        h = h + _SILL_SPREAD * k * (pad[2:] - 2 * h + pad[:-2])
        up = pad[:-2] if c > 0 else pad[2:]       # upwind neighbour (0 beyond the high edge)
        h = h - abs(c) * k * (h - up)             # the low edge's last cell pours off-screen
        h = np.maximum(0.0, h * (1 - 0.05 * k))
    s["sill"] = h
    s["ripple"] += c * dt


def _step_storm(now):
    s = _s
    if now >= s["next_bolt"]:                     # a strike: a random-walk bolt, maybe a fork
        x, y, pts, depth = _rng.uniform(16, _W - 16), 0.0, [], _rng.uniform(12, 22)
        while y < depth:
            pts.append((x, y))
            x, y = x + _rng.uniform(-3, 3), y + _rng.uniform(2, 4)
        mid = pts[len(pts) // 2] if pts else (x, 0)
        fork = [(mid[0] + 3 * i * _rng.choice((-1, 1)), mid[1] + 2 * i) for i in range(3)] if _rng.random() < 0.5 else []
        s["bolt"] = {"t0": now, "pts": pts, "fork": fork, "double": _rng.random() < 0.6}
        s["next_bolt"] = now + _rng.uniform(7, 22)


def _dot(m, x, y):
    xi, yi = int(round(x)), int(round(y))
    if 0 <= xi < _W and 0 <= yi < _H:
        m[yi, xi] ^= True


def _line(m, x0, y0, x1, y1, step=1):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(0, n, step):
        t = i / max(1, n - 1)
        _dot(m, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)


def _draw(m, now):
    s = _s
    for d in s["drops"]:                          # motion-blurred streaks along each drop's real velocity
        x0, y0 = d["x"] - d["vx"] * 0.045, d["y"] - d["vy"] * 0.045
        _line(m, x0, y0, d["x"], d["y"], 1 if d["z"] > 0.4 else 2)
        if d["hit_y"] is not None and d["hit_y"] - d["y"] < 10:   # closing in on the glass: it thickens
            _line(m, x0 + 1, y0, d["x"] + 1, d["y"])
    for p in s["splash"] + s["flying"]:
        _dot(m, p["x"], p["y"])
    for b in s["beads"]:
        x, y, r = b["x"], b["y"], b["r"]
        if r < 1.0:
            _dot(m, x, y)
        elif r < 1.6:
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                _dot(m, x + dx, y + dy)
        else:                                     # a lens, stretched taller the faster it runs, with a glint
            stretch = 0.7 + min(1.5, b["vy"] * 0.06)
            ri = int(r + 2)
            for dx in range(-ri, ri + 1):
                for dy in range(-ri - 2, ri + 1):
                    if (dx / (r + 0.2)) ** 2 + (dy / (r + stretch)) ** 2 <= 1.0:
                        _dot(m, x + dx, y + dy)
            _dot(m, x - r * 0.4, y - r * 0.5)
    h = s["sill"]                                 # the film: a line where it's wet, thicker where deep,
    film = h > 0.25                               # with gaps that travel downhill as ripples
    gaps = ((np.arange(_W) - s["ripple"]) % 7) < 1
    m[_H - 1] ^= film & ~(gaps & (h < 1.2))
    m[_H - 2] ^= h > 1.2
    bolt, flash = s["bolt"], False
    if bolt and now - bolt["t0"] < 0.3:
        t = now - bolt["t0"]
        for pts in (bolt["pts"], bolt["fork"]):
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                _line(m, x0, y0, x1, y1)
        flash = t < 0.08 or (bolt["double"] and 0.15 < t < 0.19)
    return flash


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    if not _s or now - _s["last"] > 0.5 or now < _s["last"]:
        _reset(now)                               # a fresh activation: a new seed, a new shower
    dt = max(0.0, min(0.1, now - _s["last"]))
    _s["last"] = now
    wind, rain = _weather(dt)
    _step_air(dt, wind, rain)
    _step_glass(dt, wind)
    _step_sill(dt)
    _step_storm(now)
    m = np.zeros((_H, _W), bool)
    flash = _draw(m, now)
    img = frame(d)
    if img is None:
        return
    px = np.asarray(img, dtype=bool) ^ m
    if flash:
        px = ~px                                  # the whole pane lights up
    img.frombytes(np.packbits(px, axis=1).tobytes())   # write the 1-bit panel back in place


def _pose(now):
    return math.sin(now * 0.4) * 7, -2.0, 1.0     # gazing out, slowly looking along the window


VIBE = Vibe("rain_window", mood="chill", pose=_pose, overlay=_overlay)


def _selfcheck():
    global _SEED
    from PIL import Image, ImageDraw
    img = Image.new("1", (_W, _H), 0)
    d = ImageDraw.Draw(img)

    def run(seconds, t0=0.0):
        winds, rains, beads = [], [], []
        for i in range(int(seconds * 24)):
            _overlay(d, _W, _H, t0 + i / 24)
            winds.append(_s["wind"] + _s["gust"])
            rains.append(_s["rain"])
            beads.append(len(_s["beads"]))
        return winds, rains, beads

    run(1.0, 0.0)                                 # two unseeded activations must differ
    first = sorted((round(b["x"]), round(b["y"])) for b in _s["beads"])
    run(1.0, 500.0)
    assert first != sorted((round(b["x"]), round(b["y"])) for b in _s["beads"]), "two runs started identical"

    _SEED = 1                                     # the physics, on a pinned seed
    winds, rains, beads = run(40.0, 1000.0)
    st = _s["stats"]
    assert st["splat"] > 5 and st["sill"] > 100, f"drops should both hit the pane and miss it: {st}"
    assert st["run"] > 0 and _s["wet"].max() > 0.3, "beads should run and leave wet tracks"
    assert np.std(winds) > 0.05 and np.std(rains) > 0.03, "wind and rain should wander"
    assert max(beads) <= _MAX and np.mean(beads) < 30, "the pane should stay sparse"

    _s["sill"][:] = 0.0                           # the sill drains: pour water in the middle, stop, wait
    _s["sill"][60:68] = 3.0
    total0, tilt = _s["sill"].sum(), _s["tilt"]
    for _ in range(24 * 12):
        _step_sill(1 / 24)
    h = _s["sill"]
    assert h.sum() < 0.15 * total0, f"sill should drain off the edge, kept {h.sum():.1f}/{total0:.1f}"
    _SEED = None
    print(f"rain_window ok: unique per run; {st['splat']} splats, {st['sill']} sill hits, "
          f"wind {min(winds):.2f}..{max(winds):.2f}, rain {min(rains):.2f}..{max(rains):.2f}, "
          f"beads avg {np.mean(beads):.0f}, sill drained toward {'right' if tilt > 0 else 'left'}")


if __name__ == "__main__":
    _selfcheck()
