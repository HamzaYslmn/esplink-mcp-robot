"""Black hole -- the eyes fall together and collapse into the iconic lensed disk, then the hole lives:
it flares, launches jets and tears a passing star apart. Everything evolves by real elapsed time.

1. Intro: the eyes round into two neutron stars.
2. Inspiral: a Keplerian binary losing energy to gravitational waves. Peters' law: the separation
   shrinks as a^4 ~ (t_c - t), so it drifts for seconds and then plunges; the orbit speeds up as
   Omega ~ a^-1.5 (the chirp). Close in, tides stretch each star toward the other. They merge when
   they touch.
3. Merger: a flash and a kilonova. Debris is thrown out on real (Newtonian, softened) orbits; the
   fast part escapes and fades, the bound part falls back and circularises into the disk, which
   lights up as it fills. The new hole rings down (a damped wobble of the shadow).
4. The hole, rendered the way the EHT / Interstellar images are (emission model + lensing):
     * a thin disk whose brightness follows the Novikov-Thorne profile (peaks just outside the
       inner edge), dimmed by gravitational redshift near the hole, with differential rotation
       (inner streamlines swirl faster) and relativistic Doppler beaming, delta^3, stronger
       further in where the gas moves faster;
     * the far side of the disk lensed up over the top and down under the shadow (the crown);
     * a bright photon ring hugging the round shadow; background stars lensed into two images
       pushed out to the Einstein ring.
5. Then it keeps living, a scene at a time, on a loop:
     calm -- a hot spot orbits at the inner edge; its lensed image rides over the top;
     jet  -- a bipolar outflow along the spin axis, knots racing out; the approaching jet is
             Doppler-boosted, the counter-jet faint;
     tde  -- a star falls in on a parabolic orbit, is stretched by tides and shredded into a
             stream; half the debris is bound and falls back, so the disk flares and fades
             (fallback ~ t^-5/3 falls out of the particles themselves), half escapes."""
import math
import random

from ..primitives import rounded_rect, smoothstep
from ..spec import Vibe

_CX, _CY = 64.0, 32.0
_COSI, _SINI = 0.33, 0.944    # camera inclination (~70 deg off face-on)

# -- inspiral & merger (px, s) --
_SEP0, _SEP_TOUCH = 41.0, 12.0
_T_INSPIRAL = 5.0                                         # seconds until the stars touch
_TAU = _T_INSPIRAL / (1 - (_SEP_TOUCH / _SEP0) ** 4)      # Peters: a^4 = a0^4 (1 - t/tau)
_ORBIT_K = 820.0                                          # Omega = _ORBIT_K * sep**-1.5 (Kepler III)
_T_INTRO = 1.4
_NS_R, _TIDE = 6.0, 20.0                                  # star radius; tides show inside this separation

# -- the hole & its disk (px) --
_RS0, _RS_MAX, _T_GROW = 2.0, 15.0, 6.0
_RINGS, _ASTEPS, _DISK_W, _SPIN = 10, 110, 22.0, 1.7
_GM = 40000.0                                             # px^3/s^2 for debris and the star (circular ~45 px/s at r=20)
_HS_PERIOD = 2.4                                          # s, hot-spot orbit at the inner edge
_SCENES = (("calm", 4.0), ("jet", 6.0), ("calm", 3.0), ("tde", 10.0))

_BAYER = [[(v + 0.5) / 16.0 for v in row] for row in (
    (0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))]
_STARS = [(random.Random(i).uniform(0, 140), random.Random(i + 99).uniform(2, 62),
           random.Random(i + 7).uniform(1.0, 2.5)) for i in range(14)]
_NT_PEAK = (7 / 6) ** -6 * (1 - 6 / 7)                    # Novikov-Thorne max, at r = (7/6)^2 r_in

# live state; rebuilt on (re)start. ponytail: module-level, fine for the single live engine.
_S = {"on": False, "last": None}
_rng = random.Random()


def _put(d, x, y, inten):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < 128 and 0 <= y < 64 and inten > _BAYER[y & 3][x & 3]:
        d.point((x, y), fill=1)


def _proj(x, y, z):
    """World -> (screen_x, screen_y, depth toward camera). Disk plane = x-y, spin axis = z."""
    return _CX + x, _CY + y * _COSI + z * _SINI, y * _SINI - z * _COSI


def _beam(side, r, rs):
    """Relativistic Doppler beaming, I ~ delta^3, tone-mapped for a 1-bit panel. The orbital speed
    beta ~ sqrt(rs / 2r) is higher further in, so the inner disk is the most lopsided."""
    beta = min(0.6, math.sqrt(rs / (2 * r)))
    gam = 1 / math.sqrt(1 - beta * beta)
    hi = (1 / (gam * (1 - beta))) ** 3
    return ((1 / (gam * (1 - beta * side))) ** 3 / hi) ** 0.35


def _profile(r, r_in, rs):
    """Novikov-Thorne flux (r^-3 (1 - sqrt(r_in/r))) normalised to its peak, times the
    gravitational-redshift dimming sqrt(1 - rs/r); floored so the outer disk still shows."""
    x = max(1.0, r / r_in)
    nt = x ** -3 * (1 - x ** -0.5) / _NT_PEAK
    return (0.3 + 0.7 * nt) * math.sqrt(max(0.0, 1 - rs / r))


def _ball(d, cx, cy, R, spin=None, stretch=1.0, axis=0.0, k=1.18):
    """A dithered lit sphere, optionally tidally stretched along `axis` (volume kept), with a hot
    spot riding round it (the star's spin)."""
    ca, sa = math.cos(axis), math.sin(axis)
    a, b = R * stretch, R / math.sqrt(stretch)
    lx, ly = cx - 0.42 * R, cy - 0.42 * R
    sx = sy = None
    if spin is not None:
        sx, sy = cx + 0.55 * R * math.cos(spin), cy + 0.42 * R * math.sin(spin)
    ext = int(a + 2)
    for yy in range(int(cy - ext), int(cy + ext + 1)):
        for xx in range(int(cx - ext), int(cx + ext + 1)):
            u, v = (xx - cx) * ca + (yy - cy) * sa, -(xx - cx) * sa + (yy - cy) * ca
            if (u / a) ** 2 + (v / b) ** 2 <= 1:
                val = k - math.hypot(xx - lx, yy - ly) / (2 * R)
                if sx is not None and (xx - sx) ** 2 + (yy - sy) ** 2 < (0.32 * R) ** 2:
                    val += 0.5
                _put(d, xx, yy, val)


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


# ----------------------------------------------------------------- the simulation
def _reset(now):
    _S.update(on=True, last=now, t=0.0, phase="intro", isp=0.0, theta=0.0,
              ns=[[-_SEP0 / 2, 0.0, 0.0], [_SEP0 / 2, 0.0, 0.0]], sep=_SEP0,
              gt=0.0, flash=0.0, debris=[], sc=0, sc_t=0.0, star=None, stream=[], flare=0.0)


def _inspiral(h):
    s = _S
    s["isp"] += h
    sep = max(_SEP_TOUCH, _SEP0 * max(0.0, 1 - s["isp"] / _TAU) ** 0.25)   # Peters: a^4 ~ (t_c - t)
    s["sep"] = sep
    s["theta"] += _ORBIT_K * sep ** -1.5 * h                # the chirp
    a, ct, st = sep / 2.0, math.cos(s["theta"]), math.sin(s["theta"])
    for b, sgn in ((s["ns"][0], -1), (s["ns"][1], 1)):
        b[0], b[1], b[2] = sgn * a * ct, sgn * a * st, b[2] + (3.0 + 220.0 / sep) * h
    if sep <= _SEP_TOUCH:
        s["phase"] = "merge"


def _kilonova():
    """Debris at the merger: ~35% is fast enough to escape (polar-ish, fades as it expands); the
    rest is bound, on eccentric orbits in the disk plane that drag will circularise."""
    out = []
    for i in range(80):
        a = _rng.uniform(0, 2 * math.pi)
        r0 = _rng.uniform(4, 8)
        p = [r0 * math.cos(a), r0 * math.sin(a), 0.0]
        if i < 28:
            sp = _rng.uniform(70, 120)
            el = _rng.uniform(-1.2, 1.2)
            v = [sp * math.cos(a) * math.cos(el), sp * math.sin(a) * math.cos(el), sp * math.sin(el)]
            out.append({"p": p, "v": v, "bound": False, "age": 0.0})
        else:
            vc = math.sqrt(_GM / r0)
            vt, vr = vc * _rng.uniform(0.95, 1.3), _rng.uniform(5, 25)
            v = [vr * math.cos(a) - vt * math.sin(a), vr * math.sin(a) + vt * math.cos(a), 0.0]
            out.append({"p": p, "v": v, "bound": True, "age": 0.0})
    return out


def _grav(p, h, drag=0.0):
    """One softened Newtonian kick toward the hole (drag pulls bound gas onto circular orbits)."""
    x, y, z = p["p"]
    r2 = x * x + y * y + z * z + 9.0
    r = math.sqrt(r2)
    acc = _GM / (r2 * r)
    p["v"][0] -= acc * x * h
    p["v"][1] -= acc * y * h
    p["v"][2] -= acc * z * h
    if drag:
        vc = math.sqrt(_GM / r)                              # circular velocity, prograde
        tx, ty = -y / r, x / r
        p["v"][0] += (vc * tx - p["v"][0]) * drag * h
        p["v"][1] += (vc * ty - p["v"][1]) * drag * h
        p["v"][2] -= p["v"][2] * drag * h
    for k in range(3):
        p["p"][k] += p["v"][k] * h


def _rs():
    return _RS0 + (_RS_MAX - _RS0) * smoothstep(_S["gt"] / _T_GROW)


def _step_particles(dt):
    s, rs = _S, _rs()
    n = max(1, int(dt / 0.006) + 1)
    h = dt / n
    for _ in range(n):
        for p in s["debris"]:
            if p["bound"]:
                _grav(p, h, drag=0.9)
            else:
                for k in range(3):
                    p["p"][k] += p["v"][k] * h
        for p in s["stream"]:
            _grav(p, h, drag=0.12 if p["bound"] else 0.0)
        st = s["star"]
        if st is not None:
            _grav(st, h)
    eaten = 0
    keep = []
    for p in s["debris"]:
        p["age"] += dt
        r = math.hypot(*p["p"])
        if (p["bound"] and r < rs * 1.05) or (not p["bound"] and p["age"] > 1.8):
            continue
        keep.append(p)
    s["debris"] = keep
    keep = []
    for p in s["stream"]:
        r = math.hypot(*p["p"])
        if r < rs * 1.1:
            eaten += 1                                       # fell back onto the disk -> flare
            continue
        if r < 160:
            keep.append(p)
    s["stream"] = keep
    s["flare"] = s["flare"] * math.exp(-dt / 0.8) + 0.16 * eaten


def _start_tde():
    """A star on a parabolic orbit in a plane seen nearly face-on (x-z), periapsis inside the tidal
    radius, so it is torn apart on the way round."""
    rs = _rs()
    rp, nu = rs * 2.0, -1.75
    alpha = 1.355                                            # periapsis below the hole: in from the upper right
    r = 2 * rp / (1 + math.cos(nu))
    k = math.sqrt(_GM / (2 * rp))
    vr, vt = k * math.sin(nu), k * (1 + math.cos(nu))
    ang = alpha + nu
    ex, ez = math.cos(ang), math.sin(ang)                    # radial unit (x, z)
    tx, tz = -ez, ex                                         # prograde tangent
    _S["star"] = {"p": [r * ex, 0.0, r * ez], "v": [vr * ex + vt * tx, 0.0, vr * ez + vt * tz],
                  "rt": rs * 3.0}


def _disrupt(st):
    """Tidal disruption: the star becomes a stream with a spread of orbital energies -- half bound
    (they come back), half unbound (they leave). Spread along the orbit, as the tide shears it."""
    v = st["v"]
    sp = math.sqrt(sum(c * c for c in v))
    ux, uy, uz = (c / sp for c in v)
    out = []
    for i in range(46):
        f = (i / 45) * 2 - 1                                 # -1 most bound .. +1 most unbound
        p = [st["p"][0] + ux * f * 3, st["p"][1], st["p"][2] + uz * f * 3]
        k = 1 + 0.16 * f
        out.append({"p": p, "v": [c * k for c in v], "bound": f < 0})
    _S["stream"] = out
    _S["star"] = None


def _step(now):
    s = _S
    if not s["on"] or s["last"] is None or now < s["last"] or now - s["last"] > 0.5:
        _reset(now)
        return
    dt = now - s["last"]
    s["last"] = now
    s["t"] += dt
    s["flash"] = max(0.0, s["flash"] - dt * 3.0)
    if s["phase"] == "intro":
        if s["t"] >= _T_INTRO:
            s["phase"] = "inspiral"
        return
    if s["phase"] == "inspiral":
        n = max(1, int(dt / 0.008) + 1)
        for _ in range(n):
            if s["phase"] == "inspiral":
                _inspiral(dt / n)
        return
    if s["phase"] == "merge":
        s["flash"], s["gt"], s["phase"], s["debris"] = 1.0, 0.0, "hole", _kilonova()
    s["gt"] += dt
    _step_particles(dt)
    if s["gt"] < _T_GROW:
        return
    s["sc_t"] += dt                                          # the grown hole: one scene after another
    name, dur = _SCENES[s["sc"]]
    if name == "tde" and s["star"] is None and not s["stream"] and s["sc_t"] < 1.0:
        _start_tde()
    st = s["star"]
    if st is not None and math.hypot(*st["p"]) < st["rt"]:
        _disrupt(st)
    if s["sc_t"] >= dur:
        s["sc"], s["sc_t"] = (s["sc"] + 1) % len(_SCENES), 0.0


# ----------------------------------------------------------------- drawing
def _draw_intro(d, t):
    m = smoothstep(t / _T_INTRO)
    ew = 36 - 22 * m
    rad = 12 + (ew / 2 - 12) * m
    for sgn in (1, -1):
        cx = _CX + sgn * (23.0 - 2.5 * m)
        rounded_rect(d, cx - ew / 2, _CY - ew / 2, ew, ew, rad, 1)


def _draw_stars(d, now, rs):
    """Background stars drifting by; around a hole each has two lensed images,
    r = (b +- sqrt(b^2 + 4 theta_E^2)) / 2, both pushed out toward the Einstein ring."""
    te = 1.45 * rs
    for x0, y, v in _STARS:
        x = (x0 - v * now) % 140 - 6
        if rs <= 0:
            _put(d, x, y, 0.9)
            continue
        dx, dy = x - _CX, y - _CY
        b = math.hypot(dx, dy) or 1e-3
        root = math.sqrt(b * b + 4 * te * te)
        for rr, sgn in (((b + root) / 2, 1), ((root - b) / 2, -1)):
            if rr > rs * 1.2:
                _put(d, _CX + sgn * dx / b * rr, _CY + sgn * dy / b * rr, 0.9 if sgn > 0 else 0.6)


def _draw_binary(d):
    s = _S
    tide = min(0.45, 0.45 * (_TIDE / max(s["sep"], 1)) ** 3) if s["sep"] < _TIDE * 1.6 else 0.0
    pair = sorted(s["ns"], key=lambda b: _proj(b[0], b[1], 0)[2])    # far one first
    for b in pair:
        sx, sy, _ = _proj(b[0], b[1], 0)
        ax = math.atan2((-b[1]) * _COSI, -b[0])                       # toward the companion, on screen
        _ball(d, sx, sy, _NS_R, spin=b[2], stretch=1 + tide, axis=ax)


def _draw_jets(d, now, rs, on):
    """Bipolar jets along the spin axis (screen vertical). Knots stream outward; the jet pointing
    toward us (up) is Doppler-boosted, the counter-jet (down) is faint."""
    for sgn, boost in ((-1, 1.0), (1, 0.4)):
        base = rs * 0.95
        length = 34
        for i in range(length):
            dist = base + i
            y = _CY + sgn * dist * _SINI
            knot = max(math.exp(-((i - ((now * 42 + j * 11) % length)) / 1.6) ** 2) for j in range(3))
            inten = on * boost * (0.7 + 0.8 * knot) * (1 - i / length) ** 0.5
            half = 0.8 + i * 0.07                             # a narrow opening angle
            for xx in range(int(-half), int(half) + 1):
                _put(d, _CX + xx, y, inten)


def _draw_particles(d, rs, vis):
    s = _S
    for p in s["debris"]:
        sx, sy, depth = _proj(*p["p"])
        if depth < 0 and (sx - _CX) ** 2 + (sy - _CY) ** 2 < rs * rs:
            continue                                         # behind the hole
        inten = (1.0 - 0.8 * vis) if p["bound"] else 1.0 - p["age"] / 1.8
        tx, ty, _ = _proj(*(p["p"][k] - p["v"][k] * 0.03 for k in range(3)))   # a short motion trail
        _put(d, sx, sy, inten + 0.3)
        _put(d, (sx + tx) / 2, (sy + ty) / 2, inten)
        _put(d, tx, ty, inten * 0.7)
    for p in s["stream"]:
        sx, sy, depth = _proj(*p["p"])
        if depth < 0 and (sx - _CX) ** 2 + (sy - _CY) ** 2 < rs * rs:
            continue
        _put(d, sx, sy, 0.95 if p["bound"] else 0.75)
    st = s["star"]
    if st is not None:
        sx, sy, _ = _proj(*st["p"])
        r = math.hypot(*st["p"])
        stretch = min(2.4, 1 + 1.4 * (st["rt"] / r) ** 3)   # tidal stretching on approach
        ax = math.atan2(sy - _CY, sx - _CX)
        _ball(d, sx, sy, 3.0, stretch=stretch, axis=ax, k=1.35)


def _draw_hole(d, now):
    s = _S
    g = smoothstep(s["gt"] / _T_GROW)
    rs = _RS0 + (_RS_MAX - _RS0) * g
    rph = rs * 1.13                                          # photon ring just outside the shadow
    inner = rs * 1.6                                         # disk inner edge (ISCO-like)
    vis = smoothstep(s["gt"] / 2.5)                          # the disk fills in as the debris settles
    glow = vis * (1 + min(0.9, s["flare"]))                  # a feeding flare brightens everything
    name = _SCENES[s["sc"]][0] if s["gt"] >= _T_GROW else ""
    hs = 2 * math.pi * now / _HS_PERIOD                      # hot spot azimuth
    hs_on = 1.0 if name == "calm" else 0.0
    wob = 0.22 * math.exp(-s["gt"] / 0.6) * math.sin(2 * math.pi * 2.2 * s["gt"])   # ringdown
    front = []

    _draw_stars(d, now, rs)
    for ri in range(_RINGS):                                 # the flat disk, split near/far by depth
        fr = ri / (_RINGS - 1)
        r = inner + _DISK_W * fr
        rad = _profile(r, inner, rs)
        om = _SPIN * (inner / r) ** 1.5                      # differential rotation
        for k in range(_ASTEPS):
            phi = 2 * math.pi * k / _ASTEPS
            x, y = r * math.cos(phi), r * math.sin(phi)
            sx, sy, depth = _proj(x, y, 0.0)
            tex = 0.62 + 0.38 * math.sin(phi * 3 - now * om * 1.6 + ri * 0.7)
            b = _beam(-x / r, r, rs) * rad * tex * glow
            if ri < 3:
                b += hs_on * 0.9 * math.exp(-(_wrap(phi - hs) / 0.3) ** 2) * (1 - ri / 3)
            (front.append((sx, sy, b)) if depth > 0 else _put(d, sx, sy, b))

    for ri in range(_RINGS):                                 # lensed crown: the far side bent over/under
        fr = ri / (_RINGS - 1)
        rx = rph * 1.02 + (_DISK_W * 0.42) * fr
        ry = rx * 0.82
        rad = _profile(inner + _DISK_W * fr, inner, rs)
        for k in range(_ASTEPS):
            a = 2 * math.pi * k / _ASTEPS
            cx = rx * math.cos(a)
            tex = 0.55 + 0.45 * math.sin(a * 3 - now * _SPIN + ri * 0.7 + 1.0)
            b = _beam(-cx / rx, rx, rs) * (0.45 + 0.55 * rad) * tex * glow
            if ri < 3 and math.sin(hs) < 0:                 # the hot spot's lensed image, while it's behind
                b += hs_on * 0.9 * math.exp(-(_wrap(a - hs) / 0.35) ** 2) * (1 - ri / 3)
            _put(d, _CX + cx, _CY + ry * math.sin(a), b)

    d.ellipse([_CX - rs * (1 + wob), _CY - rs * (1 - wob), _CX + rs * (1 + wob), _CY + rs * (1 - wob)], fill=0)
    steps = max(40, int(rph * 8))                            # the bright photon ring, also beamed
    for i in range(steps):
        a = 2 * math.pi * i / steps
        _put(d, _CX + rph * (1 + wob) * math.cos(a), _CY + rph * 0.96 * (1 - wob) * math.sin(a),
             1.15 * _beam(-math.cos(a), rph, rs) * glow)
    if name == "jet":
        t, dur = s["sc_t"], _SCENES[s["sc"]][1]
        _draw_jets(d, now, rs, smoothstep(t / 0.8) * smoothstep((dur - t) / 1.0))
    for sx, sy, b in front:                                  # near half of the disk, crossing in front
        _put(d, sx, sy, b)
    _draw_particles(d, rs, vis)
    if s["flash"] > 0:                                       # the merger burst
        fr = (1 - s["flash"]) * 50
        for i in range(96):
            a = 2 * math.pi * i / 96
            _put(d, _CX + fr * math.cos(a), _CY + fr * 0.6 * math.sin(a), s["flash"] * 0.9)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    d.rectangle([0, 0, W - 1, H - 1], fill=0)
    _step(now)
    ph = _S["phase"]
    if ph == "intro":
        _draw_stars(d, now, 0)
        _draw_intro(d, _S["t"])
    elif ph == "inspiral":
        _draw_stars(d, now, 0)
        _draw_binary(d)
    else:
        _draw_hole(d, now)


VIBE = Vibe("blackhole", mood="disoriented", overlay=_overlay, still=True)
