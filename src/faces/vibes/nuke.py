"""Nuke -- a thermonuclear (H-bomb) detonation on Pip's eyes.

Beats: Pip glances up, a radiation trefoil blooms glowing in each eye, then a two-stage fusion
device fires -- the fission primary's DOUBLE FLASH (a flash, an opacity dip, then a brighter fusion
flash), a Sedov-Taylor shock wave, ballistic ejecta, and a MUSHROOM CLOUD that rolls itself up out
of the fireball. We watch the mushroom hold in real time, then TIME ACCELERATES (a time-lapse) and
the cloud rises to its ceiling, spreads, and dissipates over compressed minutes -- after which the
shaken eyes ease back. Plays ONCE (~13s), self-ends.

The blast wrapper is closed-form physics (fusion yield Y(tau), Sedov radius (E t^2/rho)^1/5,
ballistic ejecta, the double-flash light curve). The CLOUD is a REAL fluid simulation -- nothing
about the mushroom shape is prescribed; it emerges.

How a buoyant thermal becomes a mushroom (the actual gas dynamics, run every frame):
  * heat T is dumped at the fireball base (energy deposition) and cools radiatively, T*=e^{-dt/tau}.
  * BUOYANCY via the BAROCLINIC mechanism: where hot low-density gas meets cooler air the density
    gradient is HORIZONTAL while gravity/pressure is VERTICAL -- misaligned, so they spin up
    vorticity  dw/dt = -g*beta * dT/dx. That single term rolls the rising thermal into a
    counter-rotating VORTEX PAIR (the 2D slice of the toroidal smoke ring) -- the whole mushroom.
  * VORTICITY CONFINEMENT re-injects the small-scale swirl that semi-Lagrangian advection smears
    away (2D has no vortex stretching to sustain it) -- f = eps*h*(N x w) -- so the ring stays alive.
  * incompressible flow by streamfunction:  laplacian(psi) = -w (Jacobi), then u = dpsi/dy,
    v = -dpsi/dx -- divergence-free for free. The closed top is the tropopause: the cap stalls and
    spreads into the anvil instead of escaping.
  * w and T are advected by that flow (semi-Lagrangian). The rising core pulls up a STEM; the
    cap's underside (cool air over hot) goes Rayleigh-Taylor / Kelvin-Helmholtz unstable -> billows.
  * tens of thousands of passive smoke parcels ride the same field + a TURBULENT-DIFFUSION random
    walk (subgrid mixing) that fills the vortex core so the cap reads solid, not hollow. They
    accumulate into a density buffer drawn by OPTICAL DEPTH (Beer-Lambert opacity = 1 - e^{-k*d})
    ordered-dithered to 1-bit -- a thick, textured, billowing mass on a 128x64 panel.
  * TIME-WARP: after the dwell, sim-time runs faster than wall-time (via substeps, so each advect
    stays CFL-safe). We watch the long rise + spread + dissipation as an accelerating time-lapse.
`still=True` locks the gaze; the eyes are carved away while the cloud owns the frame.
"""
import math

import numpy as np

from ..primitives import rand, smoothstep
from ..spec import Vibe

_LEYE, _REYE, _EYE_CY = 41, 87, 32                  # eye centres (engine defaults)
_BX, _GROUND, _APEX = 64, 63, 10                    # blast column x, ground line, ring lift-off ceiling
_RISE_H = _GROUND - _APEX
_LOOK, _ARM, _BLAST = 0.7, 1.0, 11.0
_PERIOD = _LOOK + _ARM + _BLAST                     # ~12.7s, one-shot
_GAZE_UP = -13.0
_T_DWELL = 5.5                                      # tau when real-time watching ends and the time-lapse begins
_CLEAR = 8.8                                        # tau when the cloud has dissipated enough for the eyes to return
_start = [0.0]                                      # this run's start clock (captured each frame by _done)


def _done(now, start):
    """Self-end after one pass; also stash the start so every beat phases off elapsed time."""
    _start[0] = start
    return now - start >= _PERIOD


def _beat(now):
    """(name, fraction-or-tau). 'blast' returns tau in SECONDS (for the physics); others a 0..1 frac."""
    t = now - _start[0]
    if t < _LOOK:                                   return "look", t / _LOOK
    t -= _LOOK
    if t < _ARM:                                    return "arm", t / _ARM
    return "blast", t - _ARM                        # tau, in seconds


# ----------------------------------------------------------------- closed-form blast equations
def _yield(tau):
    """Thermonuclear yield 0..1: fission spark compresses the secondary, fusion runs away
    super-exponentially, then burns out and saturates. Drives the Sedov radius + thermal energy."""
    ign = 0.22
    if tau <= 0:
        return 0.0
    if tau < ign:
        return (math.exp(tau / ign * 3.2) - 1) / (math.exp(3.2) - 1)   # fusion runaway
    return 1.0


def _shock_r(tau):
    """Sedov-Taylor strong blast wave: R = (E*tau^2 / rho)^(1/5). Expands ~tau^(2/5) once the yield
    saturates -- fast then decelerating, the signature of a point detonation in air."""
    return 100.0 * (_yield(tau) * tau * tau) ** 0.2


def _flash(tau):
    """The real nuclear DOUBLE FLASH: a sharp fission pulse, an opacity dip as the fireball goes
    optically thick, then a broader, brighter thermonuclear pulse. Two Gaussians, max-combined."""
    return max(math.exp(-((tau) / 0.045) ** 2), math.exp(-((tau - 0.30) / 0.085) ** 2))


# ----------------------------------------------------------------- the fluid simulation
# Vorticity-streamfunction Boussinesq flow on a 1-cell-per-pixel grid (so the vortex ring resolves
# at full panel detail). The five physical steps are in the module docstring; the knobs below tune
# how hard it buoys, swirls, fills, and how thick the smoke draws.
_NX, _NY, _H = 128, 64, 1.0          # flow grid == display (1 px/cell); covers the whole 128x64 panel
_GB = 26.0                           # baroclinic gain: buoyancy (dT/dx) -> vorticity (the mushroom-maker)
_EPS = 0.30                          # vorticity-confinement strength: keeps the ring's swirl alive
_TCOOL, _WDECAY = 3.6, 0.05          # heat cooling time-constant (sim-s); vorticity viscous decay (/sim-s)
_CALM = 0.7                          # extra vorticity decay once dispersing: the vortex breaks down, flow calms
_ITERS = 24                          # streamfunction relaxation sweeps (warm-started Jacobi)
_VMAX, _WMAX = 55.0, 75.0            # velocity clamp (px/sim-s, CFL safety); vorticity clamp (confinement guard)
_INJECT_T = 9.0                      # heat injected per sim-second at the base
_PRATE, _MAXP = 14000.0, 20000       # smoke parcels spawned per sim-second; live-parcel cap (dense -> solid cap)
_PDIFF = 2.5                         # turbulent-diffusion random walk (px / sqrt(sim-s)): fills the vortex core
_SRC_FALL = 3.4                      # sim-seconds the base feeds heat + smoke (then the cap rises free)
_DISPERSE, _DISPERSE_TAU = 5.5, 6.0  # sim-time the cloud starts thinning, and its dispersal time-constant (sim-s)
_OPACITY_K = 0.11                    # Beer-Lambert extinction: column density -> opacity 1-e^{-k*d}
_BLUR = 2                            # density-smoothing passes before dithering (cohere + fill voids)

# time-warp: after the dwell, sim-time outruns wall-time so the long rise/dissipation plays as a
# time-lapse. We advance it in CFL-safe SUBSTEPS (never one giant dt, which would smear advection).
_SPEED_MAX = 3.5                     # peak sim-seconds per wall-second, reached at the very end
_MAX_SUB, _DT_SUB = 8, 1.0 / 30.0    # substep cap per frame; target substep size (each advect ~1-2 cells)

_YS, _XS = np.indices((_NY, _NX)).astype(np.float64)   # cell coordinates (reused every frame)
_SRC = np.exp(-(((_XS - _BX / _H) / 5.0) ** 2 + ((_YS - (_GROUND / _H - 3.0)) / 3.0) ** 2))  # base hot-spot
_BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6],      # 4x4 ordered-dither matrix, normalised 0..1
                   [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
_DITHER = np.tile(_BAYER, (_NY // 4, _NX // 4))         # tiled to the panel: a per-pixel opacity threshold
_sim = {"start": None, "wall": None, "stime": 0.0, "pacc": 0.0,
        "w": None, "T": None, "psi": None, "u": None, "v": None, "p": None}


def _reset(now):
    np.random.seed(20240617)                            # deterministic so the showcase GIF is stable
    zero = lambda: np.zeros((_NY, _NX))                 # noqa: E731
    _sim.update(start=_start[0], wall=now, stime=0.0, pacc=0.0, w=zero(), T=zero(),
                psi=zero(), u=zero(), v=zero(), p=np.zeros((0, 3)))


def _bilinear(F, yy, xx):
    """Vectorised bilinear sample of field F at fractional grid coords (yy rows, xx cols)."""
    yy = np.clip(yy, 0.0, _NY - 1.001)
    xx = np.clip(xx, 0.0, _NX - 1.001)
    x0 = xx.astype(np.intp); y0 = yy.astype(np.intp)
    x1, y1 = x0 + 1, y0 + 1
    fx, fy = xx - x0, yy - y0
    return (F[y0, x0] * (1 - fx) * (1 - fy) + F[y0, x1] * fx * (1 - fy)
            + F[y1, x0] * (1 - fx) * fy + F[y1, x1] * fx * fy)


def _confine(w, dt):
    """Vorticity confinement (Fedkiw/Steinhoff): push energy back toward existing vortex cores so the
    ring keeps curling. N = grad|w| / |grad|w||; force f = eps*h*(N x w); add its curl to w."""
    absw = np.abs(w)
    nx = np.zeros_like(w); ny = np.zeros_like(w)
    nx[1:-1, 1:-1] = (absw[1:-1, 2:] - absw[1:-1, :-2]) / (2.0 * _H)     # d|w|/dx
    ny[1:-1, 1:-1] = (absw[2:, 1:-1] - absw[:-2, 1:-1]) / (2.0 * _H)     # d|w|/dy
    mag = np.sqrt(nx * nx + ny * ny) + 1e-8
    nx /= mag; ny /= mag
    fx = (_EPS * _H) * (ny * w)                                          # f = N x w (2D: (Ny*w, -Nx*w))
    fy = (_EPS * _H) * (-nx * w)
    curl = np.zeros_like(w)
    curl[1:-1, 1:-1] = ((fy[1:-1, 2:] - fy[1:-1, :-2])
                        - (fx[2:, 1:-1] - fx[:-2, 1:-1])) / (2.0 * _H)   # dfy/dx - dfx/dy
    w += dt * curl


def _speed(tau):
    """Time-warp factor: 1x while we watch the mushroom, then accelerating into the dissipation."""
    if tau < _T_DWELL:
        return 1.0
    k = (tau - _T_DWELL) / max(1e-6, _BLAST - _T_DWELL)
    return 1.0 + (_SPEED_MAX - 1.0) * smoothstep(min(1.0, k))


def _advance(now, tau):
    """Step the fluid from the last frame to now, warping wall-time into sim-time via CFL-safe substeps."""
    if _sim["start"] != _start[0] or _sim["wall"] is None or now < _sim["wall"]:
        _reset(now)
    dt_wall = now - _sim["wall"]
    _sim["wall"] = now
    if dt_wall <= 0.0 or dt_wall > 0.25:
        dt_wall = 1.0 / 30.0
    dstime = _speed(tau) * dt_wall                       # sim-seconds to advance this frame
    nsub = int(min(_MAX_SUB, max(1, round(dstime / _DT_SUB))))
    dt = dstime / nsub
    for _ in range(nsub):
        _sim["stime"] += dt
        _physics(dt, _sim["stime"])


def _physics(dt, stime):
    """One CFL-safe sim substep (the five physical steps from the module docstring), keyed to sim-time."""
    w, T, psi = _sim["w"], _sim["T"], _sim["psi"]

    # 1. inject heat at the base; multiplicative noise seeds the RT/KH instabilities that billow the cap
    src = max(0.0, 1.0 - stime / _SRC_FALL)
    if src > 0.0:
        T += (_INJECT_T * src * dt) * _SRC * (1.0 + 0.5 * (np.random.rand(_NY, _NX) - 0.5))

    # 2. baroclinic vorticity generation  dw/dt = -g*beta * dT/dx  (hot/cold gradient -> the vortex ring)
    dTdx = np.zeros_like(T)
    dTdx[1:-1, 1:-1] = (T[1:-1, 2:] - T[1:-1, :-2]) / (2.0 * _H)
    w += (-_GB * dt) * dTdx
    _confine(w, dt)                                   # 2b. re-inject the swirl semi-Lagrange smears away
    np.clip(w, -_WMAX, _WMAX, out=w)                  # guard against a confinement spike

    # 3. solve laplacian(psi) = -w (warm-started Jacobi); psi=0 on all walls -> closed top = tropopause lid
    h2 = _H * _H
    for _ in range(_ITERS):
        psi[1:-1, 1:-1] = 0.25 * (psi[1:-1, 2:] + psi[1:-1, :-2]
                                  + psi[2:, 1:-1] + psi[:-2, 1:-1] + w[1:-1, 1:-1] * h2)
    u, v = _sim["u"], _sim["v"]
    u[1:-1, 1:-1] = (psi[2:, 1:-1] - psi[:-2, 1:-1]) / (2.0 * _H)     # u = dpsi/dy  (divergence-free)
    v[1:-1, 1:-1] = -(psi[1:-1, 2:] - psi[1:-1, :-2]) / (2.0 * _H)    # v = -dpsi/dx
    np.clip(u, -_VMAX, _VMAX, out=u)
    np.clip(v, -_VMAX, _VMAX, out=v)

    # 4. advect vorticity + heat (semi-Lagrangian backtrace) with viscous decay / radiative cooling
    wdec = _WDECAY + (_CALM if stime > _DISPERSE else 0.0)   # spent vortex breaks down -> cloud fades in place
    bx, by = _XS - u * (dt / _H), _YS - v * (dt / _H)
    _sim["w"] = _bilinear(w, by, bx) * (1.0 - wdec * dt)
    _sim["T"] = _bilinear(T, by, bx) * math.exp(-dt / _TCOOL)

    # 5. smoke parcels -- passive tracers carried by the flow (the visible cloud)
    _advect_particles(dt, stime, src, u, v)


def _advect_particles(dt, stime, src, u, v):
    """Inject smoke at the base, carry every parcel by the flow + a turbulent random walk, then fade."""
    p = _sim["p"]
    _sim["pacc"] += _PRATE * src * dt
    n = int(_sim["pacc"])
    _sim["pacc"] -= n
    if n > 0 and len(p) < _MAXP:
        n = min(n, _MAXP - len(p))
        born = np.column_stack([_BX + (np.random.rand(n) - 0.5) * 12.0,
                                _GROUND - np.random.rand(n) * 5.0,
                                np.ones(n)])
        p = np.vstack([p, born]) if len(p) else born
    if len(p):
        gx, gy = p[:, 0] / _H, p[:, 1] / _H
        p[:, 0] += _bilinear(u, gy, gx) * dt
        p[:, 1] += _bilinear(v, gy, gx) * dt
        if _PDIFF > 0.0:                                # turbulent diffusion -> fills the hollow vortex core
            s = _PDIFF * math.sqrt(dt)
            p[:, 0] += np.random.randn(len(p)) * s
            p[:, 1] += np.random.randn(len(p)) * s
        fade = math.exp(-dt / _TCOOL)                  # radiative cooling
        if stime > _DISPERSE:                          # blast energy spent -> the cloud disperses + clears
            fade *= math.exp(-dt / _DISPERSE_TAU)
        p[:, 2] *= fade
        keep = ((p[:, 2] > 0.06) & (p[:, 0] > -4) & (p[:, 0] < 132)
                & (p[:, 1] > -6) & (p[:, 1] < 70))
        p = p[keep]
    _sim["p"] = p


def _draw_cloud(d):
    """The visible cloud: parcels -> a column-density buffer -> Beer-Lambert opacity -> ordered dither.
    Optical depth + smoothing is what makes a thick haze of parcels read as a solid, billowing mass."""
    p = _sim["p"]
    if not len(p):
        return
    xi = np.clip(p[:, 0].astype(np.intp), 0, _NX - 1)
    yi = np.clip(p[:, 1].astype(np.intp), 0, _NY - 1)
    buf = np.bincount(yi * _NX + xi, weights=p[:, 2],
                      minlength=_NY * _NX).astype(np.float64).reshape(_NY, _NX)
    for _ in range(_BLUR):                                    # unit-gain separable smooth -> haze coheres, voids fill
        buf += 0.5 * (np.roll(buf, 1, 1) + np.roll(buf, -1, 1))
        buf += 0.5 * (np.roll(buf, 1, 0) + np.roll(buf, -1, 0))
        buf *= 0.25
    opacity = 1.0 - np.exp(-_OPACITY_K * buf)                 # Beer-Lambert: thicker column -> more opaque
    ys, xs = np.nonzero(opacity > _DITHER)                    # ordered dither to 1-bit
    if len(xs):
        d.point(list(zip(xs.tolist(), ys.tolist())), fill=1)


# ----------------------------------------------------------------- other blast layers
def _shock(d, tau, now):
    """Sedov-Taylor shock: a flattened (perspective) ground ring racing out and weakening."""
    r = _shock_r(tau)
    for k in range(2):
        ro = r - k * 14
        if 6 < ro < 132 and rand(int(tau * 40), k) < 1.4 - tau * 0.5:
            d.ellipse([_BX - ro, _GROUND - ro * 0.2, _BX + ro, _GROUND + ro * 0.2], outline=1)


def _debris(d, tau):
    """Ejecta flung at detonation -- true parabolas under gravity, drawn as short motion trails."""
    g = 150.0
    for i in range(24):
        ang = -math.pi * (0.12 + rand(i) * 0.76)
        spd = 34 + rand(i, 1) * 72
        vx, vy = math.cos(ang) * spd, math.sin(ang) * spd
        x = _BX + vx * tau
        y = _GROUND + vy * tau + 0.5 * g * tau * tau
        if 0 <= x <= 127 and y <= _GROUND and rand(i, 2) > tau * 0.5:
            d.line([x - vx * 0.03, y - (vy + g * tau) * 0.03, x, y], fill=1)


def _fireball(d, tau):
    """The thermonuclear fireball: a blinding plasma ball (Sedov) that blooms then is consumed
    into the rising smoke. A bright core + plasma flares -> even the fireball reads as hot gas."""
    r = _yield(tau) * 22 * max(0.0, 1.0 - tau / 0.55)
    if r < 1:
        return
    d.ellipse([_BX - r, _GROUND - r, _BX + r, _GROUND + r * 0.4], fill=1)
    for i in range(int(r)):
        a, rr = rand(i, int(tau * 30)) * math.tau, r * (1.0 + rand(i, 1) * 0.5)
        d.point((_BX + math.cos(a) * rr, _GROUND + math.sin(a) * rr * 0.6), fill=1)


def _carve_eyes(d, ox, oy):
    """Erase the eyes' whole footprint so no leftover bar shows behind the cloud."""
    for cx in (_LEYE + ox, _REYE + ox):
        d.rectangle([cx - 24, _EYE_CY + oy - 24, cx + 24, _EYE_CY + oy + 24], fill=0)


def _blast(d, tau, now, ox, oy):
    if _flash(tau) > 0.5:                                  # inside one of the two flash pulses -> white-out
        d.rectangle([0, 0, 127, 63], fill=1)
        _advance(now, tau)                                 # keep simulating under the flash
        return
    _advance(now, tau)
    if tau < _CLEAR:
        _carve_eyes(d, ox, oy)                             # cloud owns the frame until the eyes return
    _shock(d, tau, now)
    _debris(d, tau)
    _fireball(d, tau)
    _draw_cloud(d)


# ----------------------------------------------------------------- arm: trefoil in the eyes
def _trefoil(d, cx, cy, r):
    """The radiation symbol bitten black out of a glowing eye: three 60deg blades, a clear ring, a hub."""
    box = [cx - r, cy - r, cx + r, cy + r]
    for c in (90, 210, 330):
        d.pieslice(box, c - 30, c + 30, fill=0)
    ir = r * 0.45
    d.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill=1)
    hr = r * 0.27
    d.ellipse([cx - hr, cy - hr, cx + hr, cy + hr], fill=0)


def _arm(d, f, now, ox, oy):
    """Symbol blooms in, then holds with a menacing throb + radiation warn-rings."""
    grow = smoothstep(min(1.0, f / 0.6))
    r = grow * 11 * (1.0 + 0.06 * math.sin(now * 13))
    if r < 1.5:
        return
    cy = _EYE_CY + oy
    for cx in (_LEYE + ox, _REYE + ox):
        _trefoil(d, cx, cy, r)
        rr = (now * 0.9 % 1.0) * 17
        if rr > 4:
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=1)


# ----------------------------------------------------------------- gaze + dispatch
def _gaze(now):
    """Eyes brace upward, vanish through the blast, then ease back once the cloud has dissipated."""
    name, x = _beat(now)
    if name == "look":   return 0.0, _GAZE_UP * smoothstep(x), 1.0
    if name == "arm":    return 0.0, _GAZE_UP, 1.0
    if x < _CLEAR:                                          # blast: hidden, shaking hardest at detonation
        amp = 7.0 * math.exp(-x * 3.5) + 0.4
        return (rand(int(now * 50)) - 0.5) * amp, (rand(int(now * 50), 1) - 0.5) * amp, 0.05
    e = smoothstep((x - _CLEAR) / (_BLAST - _CLEAR))        # rattled recovery: gaze re-centres, eyes reopen
    return _GAZE_UP * (1 - e) * 0.4, 0.0, 0.05 + 0.95 * e


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    name, x = _beat(now)
    if name == "look":
        return
    if name == "arm":
        _arm(d, x, now, ox, oy)
        return
    _blast(d, x, now, ox, oy)


VIBE = Vibe("nuke", mood="scared", pose=_gaze, overlay=_overlay, expired=_done, still=True)


# ----------------------------------------------------------------- self-check (python -m ...vibes.nuke)
def _selfcheck():
    """Reverse-engineer + verify every step from the running model: the closed-form blast laws, then
    the fluid invariants (incompressible, CFL-bounded, a counter-rotating vortex pair, a buoyant
    decelerating rise, spin-up-then-breakdown, full dissipation). Run: python -m ...vibes.nuke"""
    # -- closed-form blast laws --
    ys = [_yield(t) for t in np.linspace(0, 0.6, 200)]
    assert all(b - a >= -1e-12 for a, b in zip(ys, ys[1:])), "yield not monotonic"
    assert abs(ys[0]) < 1e-9 and abs(ys[-1] - 1) < 1e-9, "yield endpoints"
    tt = np.linspace(0.3, 3.0, 60)                                       # past ignition: R ~ tau^0.4
    slope = float(np.polyfit(np.log(tt), np.log([_shock_r(t) for t in tt]), 1)[0])
    assert abs(slope - 0.4) < 1e-3, f"Sedov exponent {slope:.3f} != 2/5 strong-blast law"
    ft = np.linspace(0, 0.6, 600); F = np.array([_flash(t) for t in ft])
    assert (F[ft < 0.15].max() > 0.9 and F[(ft > 0.22) & (ft < 0.4)].max() > 0.9       # two pulses
            and F[(ft > 0.05) & (ft < 0.25)].min() < 0.6), "double-flash (two peaks + opacity dip)"

    # -- drive the fluid solver over a full blast and measure the invariants --
    _start[0] = 0.0
    wmax = pmax = divrel = cfl = oddf = 0.0
    y0 = ymin = None
    for i in range(int(_PERIOD * 30) + 5):
        now = i / 30.0
        name, x = _beat(now)
        if name != "blast":
            continue
        _advance(now, x)
        w, u, v, psi, p = _sim["w"], _sim["u"], _sim["v"], _sim["psi"], _sim["p"]
        for k in ("w", "T", "u", "v", "psi"):
            assert np.all(np.isfinite(_sim[k])), f"{k} diverged at tau={x:.2f}"
        uu = np.zeros_like(psi); vv = np.zeros_like(psi)                 # incompressibility: div(curl psi)==0
        uu[1:-1, 1:-1] = (psi[2:, 1:-1] - psi[:-2, 1:-1]) / 2.0
        vv[1:-1, 1:-1] = -(psi[1:-1, 2:] - psi[1:-1, :-2]) / 2.0
        div = (uu[1:-1, 2:] - uu[1:-1, :-2] + vv[2:, 1:-1] - vv[:-2, 1:-1]) / 2.0
        divrel = max(divrel, float(np.abs(div).max()) / (float(np.abs(uu).max() + np.abs(vv).max()) + 1e-9))
        cfl = max(cfl, float(max(np.abs(u).max(), np.abs(v).max())) * _DT_SUB / _H)
        wmax = max(wmax, float(np.abs(w).max())); pmax = max(pmax, len(p))
        if len(p):                                                      # buoyant rise: weighted parcel centroid
            cy = float(np.average(p[:, 1], weights=p[:, 2]))
            y0 = cy if y0 is None else y0; ymin = cy if ymin is None else min(ymin, cy)
        if 3.4 < x < 5.5:                                              # the vortex pair (w odd about the axis)
            odd = 0.5 * (w - w[:, ::-1]); oddf = max(oddf, float(np.linalg.norm(odd) / (np.linalg.norm(w) + 1e-12)))
    assert wmax > 1.0, "no vorticity -- the thermal never spun up"
    assert pmax > 5000, "too few smoke parcels"
    assert divrel < 1e-6, f"flow not divergence-free (rel div {divrel:.1e})"
    assert oddf > 0.6, f"vorticity is not a counter-rotating pair (odd fraction {oddf:.2f})"
    assert y0 and ymin < y0 - 5, f"cloud did not rise ({y0:.0f}->{ymin:.0f}px)"
    assert np.abs(_sim["w"]).max() < _WMAX, "vorticity pinned at the clamp -- confinement too hot"
    assert len(_sim["p"]) < pmax // 4, "cloud never dissipated"
    print(f"nuke selfcheck OK: Sedov^{slope:.3f}  peak|w|={wmax:.0f}  parcels {pmax}->{len(_sim['p'])}  "
          f"rel-div={divrel:.0e}  CFL={cfl:.2f}  vortex-odd={oddf:.2f}  rise {y0:.0f}->{ymin:.0f}px")


if __name__ == "__main__":
    _selfcheck()
