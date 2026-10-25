"""Black hole -- the eyes fall together and collapse into the iconic lensed disk. Two neutron
stars (the eyes) inspiral under real two-body gravity, spinning up as they whirl in, and merge in
a flash into a seed black hole. From the debris an accretion disk lights up and the shadow grows
(R_s eases from a dot to its full size) into the Interstellar/Event-Horizon-Telescope image:

  * a one-sided disk -- the approaching side blazes, the receding side fades (relativistic Doppler
    beaming, the single most recognisable feature of every real black-hole image);
  * the disk lensed up *over the top* and down *under the bottom* of the shadow -- light from the
    far side bent around into a near-circular crown the flat disk alone never makes;
  * a bright thin photon ring hugging the round shadow.

The inspiral is a real Keplerian binary that loses energy and chirps -- it orbits faster and
faster as it falls in (Omega ~ separation^-1.5); the disk is a parametric lensed render (how
Interstellar's Gargantua and the EHT images are actually made -- an emission model plus lensing,
not free-falling dust), so it reads as a clean swirling disk instead of static. Stateful -- the
whole sequence evolves by real elapsed time."""
import math

from ..primitives import rounded_rect, smoothstep
from ..spec import Vibe

_CX, _CY = 64.0, 32.0
_COSI, _SINI = 0.33, 0.944    # camera inclination (~70 deg off face-on): foreshorten + depth split

# -- inspiral & merger: a real Keplerian binary that loses energy and spirals in (px, s) --
_SEP0 = 41.0                  # starting separation -> the two stars sit where the eyes were
_SEP_MERGE = 7.0             # they plunge together and merge below this separation
_T_INSPIRAL = 5.0            # seconds spiralling in before the merger (the long whirl)
_CHIRP = 0.45                # separation decay (1-u)^_CHIRP: a slow drift, then a rapid plunge
_ORBIT_K = 820.0             # orbital-rate scale; Omega = _ORBIT_K * sep**-1.5 (Kepler's 3rd law)
_T_INTRO = 1.4               # eyes round into two neutron stars

# -- the grown hole & its disk (px) --
_RS0, _RS_MAX = 2.0, 15.0     # shadow radius: seed -> full
_T_GROW = 6.0                 # seconds the shadow takes to grow in
_RINGS = 10                   # concentric disk streamlines
_ASTEPS = 110                 # angular samples per streamline
_DISK_W = 22.0               # disk radial extent beyond its inner edge (px)
_SPIN = 1.7                   # how fast the disk texture swirls
_DOP_FLOOR = 0.3              # receding-side brightness (vs 1.0 approaching) -> ~3x Doppler contrast

_BAYER = [[(v + 0.5) / 16.0 for v in row] for row in (
    (0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))]

# live state; rebuilt on (re)start, advanced by real dt. ponytail: module-level, fine for the single
# live engine -- make it per-engine only if ever multiplexed.
_S = {"on": False, "last": None}


def _put(d, x, y, inten):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < 128 and 0 <= y < 64 and inten > _BAYER[y & 3][x & 3]:
        d.point((x, y), fill=1)


def _proj(x, y, z):
    """World (x,y,z) -> (screen_x, screen_y, depth-toward-camera). Disk plane = x-y; the tilt
    foreshortens y and splits the disk into a near half (y>0, projects low, in front) and a far half
    (y<0, projects high, behind) -- the geometry that makes an inclined disk wrap the shadow."""
    return _CX + x, _CY + y * _COSI + z * _SINI, y * _SINI - z * _COSI


def _dop(side):
    """Relativistic Doppler beaming -> brightness on a disk point. `side` is -x/r in [-1,1]: the
    half sweeping toward the camera blazes (1.0), the receding half dims to a faint floor."""
    return _DOP_FLOOR + (1.0 - _DOP_FLOOR) * (0.5 + 0.5 * side)


def _ball(d, cx, cy, R, spin=None, k=1.18):
    """A dithered lit sphere; if `spin` is given, a bright surface spot rides round it (the star's
    rotation, visibly spun up as the pair collides)."""
    lx, ly = cx - 0.42 * R, cy - 0.42 * R
    sx = sy = None
    if spin is not None:
        sx, sy = cx + 0.55 * R * math.cos(spin), cy + 0.42 * R * math.sin(spin)
    for yy in range(int(cy - R - 1), int(cy + R + 2)):
        for xx in range(int(cx - R - 1), int(cx + R + 2)):
            if (xx - cx) ** 2 + (yy - cy) ** 2 <= R * R:
                v = k - math.hypot(xx - lx, yy - ly) / (2 * R)
                if sx is not None and (xx - sx) ** 2 + (yy - sy) ** 2 < (0.32 * R) ** 2:
                    v += 0.5                          # the rotating hot spot
                _put(d, xx, yy, v)


# ----------------------------------------------------------------- the simulation
def _reset(now):
    _S.update(on=True, last=now, t=0.0, phase="intro", isp=0.0, theta=0.0,
              ns=[[-_SEP0 / 2, 0.0, 0.0], [_SEP0 / 2, 0.0, 0.0]],   # [x, y, axial-spin]
              gt=0.0, flash=0.0)


def _inspiral(h):
    """A real gravitational inspiral: the pair orbits in the disk plane while losing energy, so the
    separation shrinks and -- by Kepler's third law (Omega ~ sep**-1.5) -- it whirls faster and
    faster (the binary 'chirp') before the final plunge into the merger."""
    s = _S
    s["isp"] += h
    u = min(1.0, s["isp"] / _T_INSPIRAL)
    sep = _SEP_MERGE + (_SEP0 - _SEP_MERGE) * (1.0 - u) ** _CHIRP
    s["theta"] += _ORBIT_K * sep ** -1.5 * h              # orbital speed climbs as they fall in
    a, ct, st = sep / 2.0, math.cos(s["theta"]), math.sin(s["theta"])
    spin_rate = 3.0 + 220.0 / sep                         # each star's own spin winds up too
    for b, sgn in ((s["ns"][0], -1), (s["ns"][1], 1)):
        b[0], b[1], b[2] = sgn * a * ct, sgn * a * st, b[2] + spin_rate * h
    if u >= 1.0:
        s["phase"] = "merge"


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
        nsub = max(1, int(dt / 0.008) + 1)                # fixed-step integration, dt-independent
        for _ in range(nsub):
            _inspiral(dt / nsub)
        return
    if s["phase"] == "merge":                             # the instant the stars touch
        s["flash"], s["gt"], s["phase"] = 1.0, 0.0, "accrete"
    s["gt"] += dt                                         # the hole + its disk grow in


# ----------------------------------------------------------------- drawing
def _draw_intro(d, t):
    m = smoothstep(t / _T_INTRO)
    ew = 36 - 22 * m
    rad = 12 + (ew / 2 - 12) * m
    for sgn in (1, -1):
        cx = _CX + sgn * (23.0 - 2.5 * m)
        rounded_rect(d, cx - ew / 2, _CY - ew / 2, ew, ew, rad, 1)


def _draw_stars(d):
    pair = sorted(_S["ns"], key=lambda b: _proj(b[0], b[1], 0)[2])    # far one first
    for b in pair:
        sx, sy, _ = _proj(b[0], b[1], 0)
        _ball(d, sx, sy, 6.5, spin=b[2])


def _draw_hole(d, now):
    s = _S
    g = smoothstep(s["gt"] / _T_GROW)
    rs = _RS0 + (_RS_MAX - _RS0) * g
    rph = rs * 1.13                                       # photon ring just outside the shadow
    inner = rs * 1.6                                      # disk inner edge (ISCO-like)
    vis = smoothstep(s["gt"] / 0.5)                       # disk lights up right after the merger
    front = []                                            # near half -> drawn over the shadow last

    # primary image of the flat disk: foreshortened ellipses, split near/far by depth
    for ri in range(_RINGS):
        fr = ri / (_RINGS - 1)
        r = inner + _DISK_W * fr
        radial = 1.0 - 0.5 * fr                           # hotter near the inner edge
        for k in range(_ASTEPS):
            phi = 2 * math.pi * k / _ASTEPS
            x, y = r * math.cos(phi), r * math.sin(phi)
            sx, sy, depth = _proj(x, y, 0.0)
            tex = 0.62 + 0.38 * math.sin(phi * 3 - now * _SPIN + ri * 0.7)   # clumps swirl round
            b = _dop(-x / r) * radial * tex * vis
            (front.append((sx, sy, b)) if depth > 0 else _put(d, sx, sy, b))

    # lensed crown: the far side bent up over the top and down under the bottom (near-circular wrap)
    for ri in range(_RINGS):
        fr = ri / (_RINGS - 1)
        rx = rph * 1.02 + (_DISK_W * 0.42) * fr
        ry = rx * 0.82                                    # far from flat -> rises high above the shadow
        radial = 1.0 - 0.55 * fr
        for k in range(_ASTEPS):
            a = 2 * math.pi * k / _ASTEPS
            cx = rx * math.cos(a)
            tex = 0.55 + 0.45 * math.sin(a * 3 - now * _SPIN + ri * 0.7 + 1.0)
            _put(d, _CX + cx, _CY + ry * math.sin(a), _dop(-cx / rx) * radial * tex * vis)

    d.ellipse([_CX - rs, _CY - rs, _CX + rs, _CY + rs], fill=0)   # the round shadow
    steps = max(40, int(rph * 8))                         # the bright photon ring (also Doppler-lit)
    for i in range(steps):
        a = 2 * math.pi * i / steps
        _put(d, _CX + rph * math.cos(a), _CY + rph * 0.96 * math.sin(a),
             1.1 * _dop(-math.cos(a)) * vis)
    for sx, sy, b in front:                              # near half of the disk, crossing in front
        _put(d, sx, sy, b)
    if s["flash"] > 0:                                   # the merger burst
        fr = (1 - s["flash"]) * 50
        for i in range(96):
            a = 2 * math.pi * i / 96
            _put(d, _CX + fr * math.cos(a), _CY + fr * 0.6 * math.sin(a), s["flash"] * 0.9)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    d.rectangle([0, 0, W - 1, H - 1], fill=0)
    _step(now)
    ph = _S["phase"]
    if ph == "intro":
        _draw_intro(d, _S["t"])
    elif ph == "inspiral":
        _draw_stars(d)
    else:
        _draw_hole(d, now)


VIBE = Vibe("blackhole", mood="disoriented", overlay=_overlay, still=True)
