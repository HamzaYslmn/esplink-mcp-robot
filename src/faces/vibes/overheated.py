"""Pip's running hot: the eyes waver behind a heat haze and thin smoke rises off the case.
(Wears `tired` -- worn-out hooded lids -- under the haze.)

Real(ish) heat physics. Hot air off the face is buoyant, so the turbulent refractive field
*rises*; we model it as a thin phase screen advecting upward and bending the light that crosses
it. Two parts:

  * Refraction -- a 2D displacement field d(x, y, t) carved into a coarse mesh and warped through
    PIL's bilinear MESH transform, so neighbouring patches shift by different amounts (local
    lens stretch/squash, sub-pixel) instead of whole scanlines sliding rigidly. Amplitude grows
    with height -- a rising plume entrains air and wanders more the higher it climbs.
  * Particles -- discrete heat motes buoying off the bottom across the face and rising, winking
    out at varied heights so the field is dense low and thins as it climbs (no connected lines).

Self-check: `cd src && uv run python -m faces.vibes.overheated`.
ponytail: O(cells) mesh per frame, fine at 128x64; bump _STEP down for a finer warp if wanted."""
import math

from PIL import Image

from ..primitives import frame, rand
from ..spec import Vibe

_RISE = 26.0       # px/s the heat haze climbs (buoyant convection)
_AMP = 3.0         # px peak lateral refraction (gentle "shimmer")
_VFRAC = 0.4       # vertical wobble as a fraction of the lateral
_STEP = 8          # mesh cell size (px) -- smaller = finer warp, more cells
_PARTS = 3        # rising heat motes
_LIFE = 2.6        # seconds a mote rises before it respawns
_PLUME = 0.92      # fraction of the height a full-life mote climbs


def _turb(x, y):   # three incommensurate octaves -> a smooth 2D turbulent field in ~[-1, 1]
    return (math.sin(x * 0.21 + y * 0.17)
            + 0.6 * math.sin(x * 0.11 - y * 0.39 + 1.3)
            + 0.35 * math.sin(x * 0.37 + y * 0.71 + 2.7)) / 1.95


def _env(y, H):    # heat rises -> shimmer grows up top; a floor keeps the whole face hazy
    return 0.3 + 0.7 * (H - 1 - y) / max(1, H - 1)


def _src(x, y, t, H):
    """Where destination pixel (x, y) samples from -> the apparent refractive shift."""
    a = _env(y, H) * _AMP
    yy = y + _RISE * t                                 # the turbulent field advects upward
    return x - a * _turb(x, yy), y - a * _VFRAC * _turb(x + 40.0, yy + 13.0)


def _refract(img, now):
    """Warp the rendered eyes through the rising haze via a bilinear mesh (sub-pixel, 2D)."""
    W, H = img.size
    mesh = []
    for gy in range(0, H, _STEP):
        for gx in range(0, W, _STEP):
            x1, y1 = min(gx + _STEP, W), min(gy + _STEP, H)
            ul, ll = _src(gx, gy, now, H), _src(gx, y1, now, H)
            lr, ur = _src(x1, y1, now, H), _src(x1, gy, now, H)
            mesh.append(((gx, gy, x1, y1),
                         (ul[0], ul[1], ll[0], ll[1], lr[0], lr[1], ur[0], ur[1])))
    warped = img.convert("L").transform((W, H), Image.MESH, mesh, Image.BILINEAR)
    img.paste(warped.point(lambda v: 255 if v >= 128 else 0).convert("1"), (0, 0))


def _heat_particles(d, W, H, now):
    """Heat motes buoying off the bottom across the face: each rises over its life and dies at a
    varied height -- so the field is dense low and thins out as it climbs."""
    base = H - 1
    for i in range(_PARTS):
        t0 = rand(i, 1) * _LIFE
        cyc = int((now + t0) / _LIFE)                        # emission cycle -> fresh spawn each rise
        u = ((now + t0) % _LIFE) / _LIFE                     # 0..1 life fraction
        if u > 0.2 + 0.8 * rand(i, cyc, 7) ** 2:             # most motes die low -> dense base, wispy top
            continue
        y = base - u * _PLUME * H * (0.8 + 0.4 * rand(i, cyc, 5))           # per-mote climb speed
        x = (4 + rand(i, cyc, 2) * (W - 8)                                  # spawn across the bottom
             + math.sin(now * 3.0 + i * 1.7) * (0.6 + 4 * u)               # turbulent sway, grows w/ height
             + (rand(i, cyc, 3) - 0.5) * 2)
        if 0 <= x < W and 0 <= y < H:
            d.point((round(x), round(y)), 1)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    img = frame(d)
    if img is None:
        return
    _refract(img, now)             # bend the eyes through the haze
    _heat_particles(d, W, H, now)  # heat motes rising off the bottom


VIBE = Vibe("overheated", mood="tired", overlay=_overlay)


def _selfcheck():
    from PIL import ImageDraw

    def white(im):                          # nonzero count -- mode "1" stores 1 or 255, both lit
        return sum(1 for v in im.get_flattened_data() if v)

    img = Image.new("1", (128, 64), 0)
    d = ImageDraw.Draw(img)
    d.rectangle([46, 22, 82, 42], fill=1)                     # stand-in eyes
    n0 = white(img)
    assert n0 > 0
    assert any(abs(_src(x, 30, 1.3, 64)[0] - x) >= 1.0 for x in range(128)), "field never refracts"
    _refract(img, 1.3)
    n1 = white(img)
    assert n1 > 0, "warp erased the eyes"
    assert abs(n1 - n0) <= n0 * 0.4, "warp should displace ink, not destroy it"
    _heat_particles(d, 128, 64, 1.3)
    n2 = white(img)
    assert n2 > n1, "no heat particles drawn"
    print(f"overheated ok: white {n0} -> warp {n1} -> +particles {n2}")


if __name__ == "__main__":
    _selfcheck()
