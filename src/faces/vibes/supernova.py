"""Supernova -- a massive star's core-collapse death, the real sequence end to end on Pip's eyes.

The textbook sequence has 54 steps (main-sequence ignition -> remnant). A star does NOT just explode:
it lives a long fusion-supported life and SWELLS (core contracts between fuel stages while shell burning
puffs the envelope into a supergiant [steps 1-15]); only when the iron core can no longer fuse for net
energy [17], electron capture drains its degeneracy pressure [18] and photodisintegration saps its heat
[19], does it lose the fight with gravity [20] and COLLAPSE [21]. So the on-screen order is expand-then-
collapse, exactly as asked -- the grow phase is that whole burning life, and the loss of support is faked
by the soft (gamma<4/3, dynamically unstable) equation of state plus a whisper of seed infall.

Physics model (1D spherical Lagrangian hydro -- the von Neumann-Richtmyer scheme that actually bounces):
  * Shells carry radius r, velocity v, specific internal energy eps; self-gravity (star only) + pressure.
  * EoS P=(gamma(rho)-1) rho eps with soft gamma below nuclear density (collapse) -> stiff gamma above it
    (the inner core halts and rebounds -- the bounce).
  * von Neumann-Richtmyer artificial viscosity Q captures the shock over a few zones and heats eps.
  * First-law energy eps' = -(P+Q) dV/dm; a delayed neutrino-driven deposit in the gain region revives
    the stalled prompt shock -- the modern explosion mechanism.
  * Emission is optically thin (rho^2), temperature gated (cold un-shocked wind is dark), line-of-sight
    integrated through the sphere (limb-brightened shell).

On-screen phases, mapped to the real steps (the hydro genuinely simulates 21-41; the long life and the
late light curve are compressed/rendered, since a toy EoS has neither nuclear networks nor a light curve):
  1. _intro  -- the two eyes merge and round into the newborn star.                           [main sequence, 1]
  2. _grow   -- the star swells through its fusion-supported life to a red/supergiant.   [core burning -> Fe, 1-15]
  3. collapse + bounce -- iron core goes unstable, implodes subsonically/supersonically, reaches nuclear
     density, traps neutrinos, forms a proto-neutron star and REBOUNDS, launching a shock.        [16-28]
  4. stall + revival -- the prompt shock loses energy to photodisintegration/neutrinos and STALLS; delayed
     neutrino heating behind it revives the shock and launches the explosion.                     [29-40]
  5. explosion + shell -- the shock accelerates out through the mantle and the ejecta sweep the wind into a
     hollow, limb-brightened expanding shell.                                                     [41-47]
  6. breakout flash -- the shock reaches the surface: the first electromagnetic flash.            [45-46, 48]
  7. remnant -- the ejecta thin and fade, leaving a compact neutron star that lights as a pulsar: the
     magnetic axis is tilted off the spin axis and cones round it as the star rotates about its own axis
     (a lighthouse, not a flat propeller). Magnetospheric, so rendered -- a bare ideal-gas EoS holds no
     neutron star, and the beam never pushes the ejecta (it is light on the gas, not a force in it). [52-54]
"""
import math

import numpy as np

from ..primitives import smoothstep
from ..spec import Vibe

# ---- panel / render geometry ----
_W, _H = 128, 64
_CX, _CY = 64.0, 32.0
_SCALE = 22.0           # sim length unit -> px (progenitor radius R_STAR=1 fills the eyes at ~22px)

# ---- the star + its stellar-wind circumstellar medium ----
_N_STAR, _R_STAR, _M_STAR = 90, 1.0, 1.0        # equal-mass shells; the bound, self-gravitating star
_N_AMB, _R_AMB, _RHO_W = 110, 5.5, 0.05         # cold r^-2 wind shells out to R_AMB; density at the surface
_N = _N_STAR + _N_AMB

# ---- 1D Lagrangian hydro ----
_G = 1.0
_GAM_SOFT, _GAM_STIFF = 1.20, 2.5    # adiabatic index: <4/3 collapses, >4/3 (above rho_nuc) bounces
_RHO_NUC, _NUCP = 60.0, 6.0          # nuclear density where the EoS stiffens; sharpness of the crossover
_CQ, _CL = 3.0, 1.0                  # von Neumann-Richtmyer artificial viscosity (quadratic, linear)
_P_FAC, _V_SEED = 0.80, 0.07         # start the star under-pressured + a whisper of infall: runs out of fuel sooner
_HEAT_RATE, _HEAT_WIN = 6.8, 0.78    # delayed neutrino-driven revival: rate + window after bounce
_HEAT_LO, _HEAT_HI = 0.3, 0.6        # the gain region: rho in (_HEAT_LO, _HEAT_HI*rho_nuc) behind the shock
_EPS_FLOOR = 1e-8
_CFL, _MAX_SUB = 0.30, 110
_4PI = 4.0 * math.pi
_4PI3 = _4PI / 3.0

# ---- pacing: wall-time -> sim-time, with bullet-time through the bounce, then a held remnant ----
_T_INTRO = 0.9          # eyes merge and round into the newborn-star sphere
_T_EXPAND = 1.5         # the envelope swells into a supergiant as core fusion runs through its fuels
_GROW_SEED = 12.0       # newborn-star sphere radius (px) the eyes merge into, before it expands
_GROW_GAIN = 1.25       # limb-darkened sphere brightness -- shared by intro/grow so the hand-off is seamless
_HANDOFF = 0.62         # fraction of the grow phase after which it crossfades into the live hydro field
_SIM_RATE = 1.05        # base sim-seconds per wall-second (fast through the slow fuel-burning life)
_SIM_TAU = 0.20         # smooth wall-time jitter before it reaches the hydro clock
_BULLET = 0.22          # slow to this fraction near the bounce so we savour the rebound
_T_FREEZE = 10.0        # sim-seconds: the ejecta has flown off and thinned -> freeze on the lone pulsar

# ---- look: rho^2 emission, temperature-gated, line-of-sight projected ----
_EM_REF, _EM_P = 0.012, 0.5          # LOS emission column -> brightness (power-law)
_EPS_HOT = 0.05                      # temperature gate: only shock-heated gas emits (cold wind is dark)
_B_FLOOR = 0.34                      # brightness floor: faint diffuse gas -> pure black space (no dot haze)
_NZ = 64                             # line-of-sight samples through the sphere
_RT_SIGMA, _RT_MAX = 2.1, 4.0        # Rayleigh-Taylor shell-ripple growth rate (/sim-s) and amplitude cap (px)
_RT_MODES = 9                        # more modes -> filamentary, less of a symmetric "flower"
_FLASH_DECAY, _FLASH_R = 1.9, 55.0
_LUMA_TAU = 0.085                    # display phosphor / retinal persistence: smooth dither threshold chatter
_SPACE_CUT = 0.055                   # below this, emit true black; no isolated dither pixels in space
_FLASH_SPEED, _FLASH_W = 98.0, 3.6  # shock flash expands outward; it never shrinks back into a ball

# ---- pulsar remnant (beams are magnetospheric -> rendered, not simulated) ----
_SPIN = 2.0 * math.pi / 2.8          # the star rotates about its spin axis: one turn per ~2.8 s
_OBLIQ = 1.18                        # magnetic-axis tilt off the spin axis (rad): the cone the beam sweeps
_COS_OBL, _SIN_OBL = math.cos(_OBLIQ), math.sin(_OBLIQ)
_AXIS = np.array([0.33, -0.86, 0.40]); _AXIS /= np.linalg.norm(_AXIS)   # spin axis: up, tilted, leaning toward viewer
_AXU = np.cross(_AXIS, [0.0, 0.0, 1.0]); _AXU /= np.linalg.norm(_AXU)   # an orthonormal spin-plane basis (axis ⟂ u,w)
_AXW = np.cross(_AXIS, _AXU)
_JET_LEN, _JET_HALF = 72.0, 0.12     # beam reach (px) and cone half-angle (rad) -> long, narrow jets
_JET_GAIN = 1.7                      # beam brightness -> a solid clean ray, not a dithered fuzzy band
_JET_RAMP, _JET_DELAY = 2.6, 1.8     # wall-s: jets bloom in after bounce, once the shell has opened up
_NS_R = 2.3                          # neutron-star core radius (px)

_BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6],
                    [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16.0
_DITHER = np.tile(_BAYER, (_H // 4, _W // 4))            # per-pixel opacity threshold
_YS, _XS = np.indices((_H, _W)).astype(np.float64)
_RAD = np.hypot(_XS - _CX, _YS - _CY)                    # per-pixel impact parameter (px)
_ANG = np.arctan2(_YS - _CY, _XS - _CX)
_ZS = np.linspace(-_R_AMB, _R_AMB, _NZ)                  # line-of-sight depth samples (sim units)
_DZ = float(_ZS[1] - _ZS[0])
_GRAV = (np.arange(1, _N + 1) <= _N_STAR).astype(np.float64)   # gravity binds the star shells only

_S = {"born": None, "wall": None}


def _gamma(rho):
    """Adiabatic index vs density: soft (<4/3, unstable) below nuclear density, stiff (->~2.5) above."""
    x = (rho / _RHO_NUC) ** _NUCP
    return _GAM_SOFT + (_GAM_STIFF - _GAM_SOFT) * x / (1.0 + x)


# ---------------------------------------------------------------- initial star + wind
def _reset(now):
    """Build the progenitor: a near-hydrostatic, dynamically-unstable star inside a cold r^-2 wind."""
    np.random.seed(8675309)                              # deterministic showcase
    fine = np.linspace(0.0, _R_AMB, 9000)
    star = np.clip(1.0 - (fine / _R_STAR) ** 2, 0.0, None)
    dmdr = _4PI * fine ** 2 * star
    mstar = float(np.sum(0.5 * (dmdr[1:] + dmdr[:-1]) * np.diff(fine)))
    star *= _M_STAR / mstar
    wind = _RHO_W * (_R_STAR / np.maximum(fine, _R_STAR)) ** 2     # r^-2 progenitor wind (CSM)
    prof = np.where(fine < _R_STAR, star, wind)                    # clean stellar surface, then the wind (a contact)
    dmdr = _4PI * fine ** 2 * prof
    menc = np.concatenate([[0.0], np.cumsum(0.5 * (dmdr[1:] + dmdr[:-1]) * np.diff(fine))])
    M_in = float(np.interp(_R_STAR, fine, menc))
    r = np.concatenate([np.interp(np.linspace(0.0, M_in, _N_STAR + 1), menc, fine),   # equal-mass star shells
                        np.linspace(_R_STAR, _R_AMB, _N_AMB + 1)[1:]])                 # equal-radius wind shells
    r[0] = 0.0
    m = np.interp(r, fine, menc)
    dm = np.diff(m)
    V = np.maximum(_4PI3 * (r[1:] ** 3 - r[:-1] ** 3), 1e-12)
    rho = dm / V
    P = np.zeros(_N)                                     # ISOLATED-star hydrostatic P (P=0 at the surface,
    for j in range(_N_STAR - 2, -1, -1):                # integrate inward through the star only -- the wind's
        g = _G * m[j + 1] / max(r[j + 1], 1e-6) ** 2    # weight must NOT over-support the star or it won't collapse
        P[j] = P[j + 1] + g * rho[j] * (r[j + 1] - r[j])
    eps = np.where(r[1:] < _R_STAR, _P_FAC * P / np.maximum((_gamma(rho) - 1.0) * rho, 1e-12), _EPS_FLOOR)
    eps = np.maximum(eps, _EPS_FLOOR)                    # the wind is COLD -> dark until shock-heated
    v = np.where(r < _R_STAR, -_V_SEED * r / _R_STAR, 0.0)     # gentle inward infall seeds a smooth collapse
    v[0] = 0.0
    ns = np.random.randint(2, 16, _RT_MODES)             # RT seed: broad angular modes; phases advect after bounce
    ph = np.random.rand(_RT_MODES) * 2 * math.pi
    bk = np.random.rand(_RT_MODES); bk /= bk.sum()
    drift = (np.random.rand(_RT_MODES) * 2.0 - 1.0) * np.linspace(0.025, 0.16, _RT_MODES)
    fingers = sum(b * np.sin(n * _ANG + p) for n, p, b in zip(ns, ph, bk))
    _S.update(born=now, wall=now, t_sim=0.0, r=r, v=v, eps=eps, dm=dm, m=m,
              rho_c=rho[0], rho_c0=rho[0], t_bounce=0.0, t_bounce_wall=None, flash=0.0, flash_age=0.0,
              bounced=False, broke=False, rt=0.0, fingers=fingers, rt_modes=ns, rt_phase=ph,
              rt_weight=bk, rt_drift=drift, sim_rate=_SIM_RATE, luma=None, draw_wall=now)


# ---------------------------------------------------------------- the integrator
def _state():
    """Live (rho, gamma, P, c_s) from the shell geometry + EoS."""
    r, eps = _S["r"], _S["eps"]
    V = np.maximum(_4PI3 * (r[1:] ** 3 - r[:-1] ** 3), 1e-12)
    rho = _S["dm"] / V
    gam = _gamma(rho)
    P = (gam - 1.0) * rho * eps
    cs = np.sqrt(np.maximum(gam * P / rho, 0.0))
    return V, rho, gam, P, cs


def _cfl_dt():
    """Largest CFL-safe step from the current state (sound speed + bulk motion across a shell)."""
    r, v = _S["r"], _S["v"]
    _, _, _, _, cs = _state()
    dr = np.maximum(r[1:] - r[:-1], 1e-4)
    sp = cs + np.abs(0.5 * (v[1:] + v[:-1]))
    return max(1e-6, _CFL * float(np.min(dr / (sp + 1e-9))))


def _step(dt):
    """One hydro step: gravity (star only) + pressure + artificial-viscosity shock, then the energy update."""
    r, v, eps, dm, m = _S["r"], _S["v"], _S["eps"], _S["dm"], _S["m"]
    V, rho, gam, P, cs = _state()
    dvz = v[1:] - v[:-1]                                  # velocity jump across each shell
    Q = np.where(dvz < 0.0, _CQ * rho * dvz ** 2 + _CL * rho * cs * (-dvz), 0.0)   # shock viscosity (compression only)
    Pt = P + Q
    dP = np.diff(np.append(Pt, 0.0))                     # pressure across boundaries 1..N (outer vacuum)
    dm_face = np.empty(_N)                               # mass associated with each moving boundary
    dm_face[:-1] = 0.5 * (dm[1:] + dm[:-1])
    dm_face[-1] = 0.5 * dm[-1]
    ri = r[1:]
    a = -_G * _GRAV * m[1:] / ri ** 2 - _4PI * ri ** 2 * dP / dm_face
    v_new = v.copy(); v_new[1:] = v[1:] + a * dt; v_new[0] = 0.0
    r_new = r.copy(); r_new[1:] = r[1:] + v_new[1:] * dt
    r_new = np.maximum.accumulate(r_new)                 # forbid shell crossing (Lagrangian guard)
    V_new = np.maximum(_4PI3 * (r_new[1:] ** 3 - r_new[:-1] ** 3), 1e-12)
    eps = np.maximum(eps - Pt * (V_new - V) / dm, _EPS_FLOOR)   # PdV work + shock heating
    _S["r"], _S["v"], _S["eps"] = r_new, v_new, eps


def _heat(dt):
    """Delayed neutrino-driven revival: neutrino heating ramps up and down in the gain region instead
    of switching on like a lamp, so the stalled shock is revived by a smooth pressure rise."""
    r = _S["r"]
    rho = _S["dm"] / np.maximum(_4PI3 * (r[1:] ** 3 - r[:-1] ** 3), 1e-12)
    gain = (rho > _HEAT_LO) & (rho < _RHO_NUC * _HEAT_HI)
    if not np.any(gain):
        return
    u = (_S["t_sim"] - _S["t_bounce"]) / _HEAT_WIN
    pulse = smoothstep(u / 0.22) * (1.0 - smoothstep((u - 0.58) / 0.42))
    lo = np.clip((rho - _HEAT_LO) / max(_HEAT_LO, 1e-9), 0.0, 1.0)
    hi = np.clip((_RHO_NUC * _HEAT_HI - rho) / (_RHO_NUC * _HEAT_HI), 0.0, 1.0)
    profile = lo * hi
    _S["eps"][gain] += _HEAT_RATE * pulse * profile[gain] * dt


def _events(dt):
    """Read collapse landmarks off the live state (emergent timing, not scripted): core bounce at
    nuclear density [27-28], shock breakout at the surface [45-46], and Rayleigh-Taylor shell growth."""
    s = _S
    r, v = s["r"], s["v"]
    rho_c = s["dm"][0] / max(_4PI3 * r[1] ** 3, 1e-12)    # central-shell density
    if not s["bounced"] and rho_c > 10.0 * s["rho_c0"] and v[1] > 0.0:   # core slammed nuclear + rebounding
        s["bounced"], s["flash"], s["rt"], s["t_bounce"] = True, 1.0, 0.5, s["t_sim"]
        s["flash_age"] = 0.0
    s["rho_c"] = rho_c
    if s["bounced"]:
        idx = int(np.argmax(v))                          # the out-running shock = peak outward velocity
        if not s["broke"] and v[idx] > 0.0 and idx >= _N_STAR:
            s["broke"], s["flash"], s["flash_age"] = True, 1.0, 0.0   # shock reaches the surface -> breakout flash
        s["rt"] = min(_RT_MAX, s["rt"] * math.exp(_RT_SIGMA * dt))   # Rayleigh-Taylor shell ripples grow


def _advance(now):
    """Warp wall-time into sim-time and integrate in CFL-safe substeps (slow-mo through the bounce).
    Freezes once the remnant has bloomed -- the pulsar then just spins on wall-time."""
    s = _S
    dt_wall = now - s["wall"]
    s["wall"] = now
    if dt_wall <= 0.0 or dt_wall > 0.25:
        dt_wall = 1.0 / 30.0
    if s["t_sim"] < _T_FREEZE:                                   # still evolving -> integrate the hydro
        near = smoothstep((s["rho_c"] / _RHO_NUC - 0.3) / 0.7)   # ramp into bullet-time as the core nears nuclear
        target_rate = _SIM_RATE * (1.0 - (1.0 - _BULLET) * near)
        a = 1.0 - math.exp(-dt_wall / _SIM_TAU)
        s["sim_rate"] = s.get("sim_rate", _SIM_RATE) + (target_rate - s.get("sim_rate", _SIM_RATE)) * a
        want = s["sim_rate"] * dt_wall
        nsub = 0
        while want > 1e-9 and nsub < _MAX_SUB:
            dt = min(_cfl_dt(), want)
            _step(dt)
            if s["bounced"] and s["t_sim"] - s["t_bounce"] < _HEAT_WIN:
                _heat(dt)                                # revive the stalled shock -> the explosion
            _events(dt)
            s["t_sim"] += dt
            want -= dt
            nsub += 1
        if s["flash"] > 0.0:
            s["flash_age"] = s.get("flash_age", 0.0) + dt_wall
            s["flash"] = max(0.0, s["flash"] - _FLASH_DECAY * dt_wall)
    if s["bounced"] and s["t_bounce_wall"] is None:              # pulsar's birth -> anchor the beam fade-in
        s["t_bounce_wall"] = now


# ---------------------------------------------------------------- drawing (one field, every frame)
def _emission():
    """Per-shell optically-thin emission measure (rho^2) gated by temperature: only shock-heated
    gas glows, cold un-shocked wind is dark. Returns (zone-centre radii, emission)."""
    r, eps, dm = _S["r"], _S["eps"], _S["dm"]
    rho = dm / np.maximum(_4PI3 * (r[1:] ** 3 - r[:-1] ** 3), 1e-12)
    rc = np.maximum.accumulate(0.5 * (r[1:] + r[:-1])) + 1e-6 * np.arange(_N)
    return rc, rho ** 2 * np.clip(eps / _EPS_HOT - 1.0, 0.0, 1.0)   # hard floor -> cold un-shocked wind is black


def _column(bimp):
    """Line-of-sight integral of the emission through the sphere -> limb-brightened shell (a 2D field)."""
    rc, em = _emission()
    col = np.zeros((_H, _W))
    for z in _ZS:
        col += np.interp(np.sqrt(bimp * bimp + z * z), rc, em, left=em[0], right=0.0) * _DZ
    return col


def _rt_fingers(t):
    """Rayleigh-Taylor fingers are seeded modes that advect slowly around the contact surface."""
    ns = _S.get("rt_modes")
    if ns is None:
        return _S["fingers"]
    ph = _S["rt_phase"] + _S["rt_drift"] * t
    return sum(b * np.sin(n * _ANG + p) for n, p, b in zip(ns, ph, _S["rt_weight"]))


def _smooth_luma(b, now):
    """Low-pass only the rendered light, not the hydro, to remove frame-rate dither sparkle."""
    s = _S
    prev = s.get("luma")
    if prev is None or np.shape(prev) != np.shape(b):
        s["luma"], s["draw_wall"] = b, now
        return b
    dt = max(1.0 / 240.0, min(now - s.get("draw_wall", now), 0.2))
    s["draw_wall"] = now
    rise = 1.0 - math.exp(-dt / (_LUMA_TAU * 0.55))
    fall = 1.0 - math.exp(-dt / _LUMA_TAU)
    a = np.where(b > prev, rise, fall)
    out = prev + (b - prev) * a
    s["luma"] = out
    return out


def _jets(now):
    """The pulsar's two opposing beams as a true lighthouse: the magnetic axis is tilted off the spin
    axis (_OBLIQ) and CONES around it as the star rotates about its own axis. Projected to the screen
    each beam swings, foreshortens as it tips out of the image plane, brightens as it points toward the
    viewer, and flashes when it swings straight at us -- a rotating star, not a flat in-plane propeller.
    Magnetospheric, so rendered (not fluid); a brightness field that fades in after the bounce."""
    s = _S
    amp = smoothstep((now - s["t_bounce_wall"] - _JET_DELAY) / _JET_RAMP)
    if amp <= 0.0:
        return 0.0
    phi = now * _SPIN
    beam = _COS_OBL * _AXIS + _SIN_OBL * (math.cos(phi) * _AXU + math.sin(phi) * _AXW)   # cones around the axis
    jb = np.zeros((_H, _W))
    pulse = 0.0
    for e in (beam, -beam):                              # the two opposing poles
        f = math.hypot(e[0], e[1])                       # in-plane fraction -> the projected beam foreshortens
        reach = _JET_LEN * f
        if reach >= 1.0:
            dang = np.abs(((_ANG - math.atan2(e[1], e[0]) + math.pi) % (2 * math.pi)) - math.pi)
            cone = np.clip(1.0 - dang / _JET_HALF, 0.0, 1.0) ** 2
            radial = np.clip(1.0 - _RAD / reach, 0.0, 1.0)
            jb = np.maximum(jb, cone * radial * (0.35 + 0.65 * max(e[2], 0.0)))   # toward the viewer -> brighter
        pulse = max(pulse, smoothstep((e[2] - 0.80) / 0.20))     # swung onto the line of sight -> a flash at us
    if pulse > 0.0:
        jb = np.maximum(jb, pulse * np.exp(-0.5 * (_RAD / 3.2) ** 2))
    return jb * amp * _JET_GAIN


def _draw_ns(d, now):
    """The neutron star itself: a tiny brilliant core at the heart of the nebula."""
    amp = smoothstep((now - _S["t_bounce_wall"]) / 0.8)
    rns = _NS_R * amp
    if rns > 0.4:
        d.ellipse([_CX - rns, _CY - rns, _CX + rns, _CY + rns], fill=1)


def _draw_flash(d):
    """An explosion flash is an outgoing shock front. It expands and fades; it never contracts."""
    s = _S
    age = s.get("flash_age", 0.0)
    rf = min(_FLASH_R, 5.0 + _FLASH_SPEED * age)
    width = _FLASH_W + 9.0 * (1.0 - s["flash"])
    ring = s["flash"] * np.exp(-0.5 * ((_RAD - rf) / width) ** 2)
    ring = np.where(ring >= _SPACE_CUT, ring, 0.0)
    ys, xs = np.nonzero(ring > _DITHER)
    if len(xs):
        d.point(list(zip(xs.tolist(), ys.tolist())), fill=1)


def _blit(d, b):
    """One brightness field -> ordered-dither points. The single output path for every phase, so the
    intro, the grow and the live sim all read the same and can't pop at a hand-off."""
    b = np.where(b >= _SPACE_CUT, b, 0.0)
    ys, xs = np.nonzero(b > _DITHER)
    if len(xs):
        d.point(list(zip(xs.tolist(), ys.tolist())), fill=1)


def _sphere_b(R, gain=_GROW_GAIN):
    """A near-solid star disc of radius R (px) with a soft limb -- the shape the eyes become and the
    star grows from. Flat-topped (high power) so it reads the same as the live hydro disc and the
    grow -> hydro hand-off is solid-to-solid, with no grainy gradient seam."""
    return np.clip(gain * (1.0 - (_RAD / max(R, 1e-6)) ** 6), 0.0, 1.0)


def _field_b(now):
    """The live hydro picture as a brightness field (pre-dither): temperature-gated rho^2 emission,
    LOS-projected (limb-brightened shell), with the pulsar beams blended in once it has bounced."""
    s = _S
    rt_age = max(0.0, s["t_sim"] - s["t_bounce"]) if s["bounced"] else 0.0
    bimp = np.clip((_RAD - s["rt"] * _rt_fingers(rt_age)) / _SCALE, 0.0, None)   # RT fingers ripple the shell
    b = np.clip((_column(bimp) / _EM_REF) ** _EM_P, 0.0, 1.0)
    b = np.clip((b - _B_FLOOR) / (1.0 - _B_FLOOR), 0.0, 1.0)              # faint diffuse gas -> black; space stays black
    if s["bounced"]:
        b = np.maximum(b, _jets(now))                    # beams emerge from the explosion, no hand-off pop
    return _smooth_luma(b, now)


def _draw_field(d, now):
    """The whole picture: the live emission field, dithered; plus the flash and the crisp neutron star."""
    s = _S
    _blit(d, _field_b(now))
    if s["flash"] > 0.02:                                # bounce/breakout: outward shock flash, not a shrinking ball
        _draw_flash(d)
    if s["bounced"]:
        _draw_ns(d, now)                                 # the persistent neutron star core


def _intro_b(u):
    """Phase 1 [step 1]: the two eyes drift together and melt into one limb-darkened sphere -- the
    star igniting on the main sequence. The melt lands exactly on the sphere the grow phase starts
    from, so intro -> grow never jumps."""
    m = smoothstep(u)                                    # eye centres drift to the middle
    fuse = smoothstep((u - 0.28) / 0.72)                 # ... and the two shapes dissolve into one sphere
    rx = 18.0 + (_GROW_SEED - 18.0) * m                  # wide ellipses round toward the seed radius
    ry = 10.5 + (_GROW_SEED - 10.5) * m
    eyes = np.zeros((_H, _W))
    for cx0 in (41.0, 87.0):
        cx = cx0 + (_CX - cx0) * m
        q = ((_XS - cx) / max(rx, 1e-6)) ** 2 + ((_YS - _CY) / max(ry, 1e-6)) ** 2
        eyes = np.maximum(eyes, np.clip(_GROW_GAIN * (1.0 - q ** 3), 0.0, 1.0))   # solid eyes, like the star
    return (1.0 - fuse) * eyes + fuse * _sphere_b(_GROW_SEED)


def _grow_b(u):
    """Phase 2 [steps 1-15]: the star swells monotonically to the sim's start radius -- its whole
    fusion-supported life, core burning H -> He -> ... -> Fe while the envelope puffs to a supergiant."""
    R = _GROW_SEED + (_R_STAR * _SCALE - _GROW_SEED) * smoothstep(u)
    return _sphere_b(R)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    d.rectangle([0, 0, W - 1, H - 1], fill=0)            # the star / remnant owns the whole frame
    s = _S
    if s["born"] is None or s["wall"] is None or now < s["wall"] or now - s["wall"] > 0.5:
        _reset(now)
    age = now - s["born"]
    if age < _T_INTRO:                                   # eyes -> newborn star
        _blit(d, _intro_b(age / _T_INTRO))
        s["wall"] = now                                  # pin the sim clock until the collapse begins
        return
    if age < _T_INTRO + _T_EXPAND:                       # fusion fails -> the envelope swells to a supergiant
        u = (age - _T_INTRO) / _T_EXPAND
        b = _grow_b(u)
        if u > _HANDOFF:                                 # crossfade the analytic sphere into the live emission
            x = smoothstep((u - _HANDOFF) / (1.0 - _HANDOFF))   # field is the static t=0 star -> matches the first sim frame
            b = (1.0 - x) * b + x * _field_b(now)
        _blit(d, b)
        s["wall"] = now
        return
    _advance(now)
    if not np.isfinite(s["r"]).all():                    # numerical safety -> start over (rare)
        _reset(now)
        return
    _draw_field(d, now)


VIBE = Vibe("supernova", mood="awe", overlay=_overlay, still=True)
