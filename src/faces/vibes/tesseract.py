"""Tesseract -- Pip's eyes dissolve into the fourth dimension, then a 4D hypercube turns slowly
inside-out. The spin is the cleanest real 4D motion there is: a *simple rotation* -- constant angular
velocity in a single rotation plane of SO(4) (uniform circular motion, one bivector generator), not a
tumbling free body. We animate one plane only -- the x-w plane, which couples a spatial axis with the
fourth dimension -- so the inner cube swells out through the outer one and back, the iconic tesseract
turn. The body is viewed from a *fixed* 3/4 tilt (a constant 3D reorientation), so the cube-within-a-
cube structure stays legible on the flat panel: one steady, predictable, perfectly periodic rotation
instead of an all-planes precession.

The cube is also born from a singularity: the 4D->3D perspective starts far away so it unfolds out of
a point while the eyes erode outward-first, grain by grain, getting pulled into the growing wireframe.

Depth is read off solid lines (dithered stipple was unreadable at 64px): edges nearer the camera --
in combined 4D(w, weighted heavier) + 3D(z) distance -- are drawn **bold (2px)**, far edges **thin
(1px)**, and they're painted far-to-near so the near cell overlays the far one. That line-weight
perspective keeps the inner cube clearly visible while still cueing which cell is in front.

Refs: simple vs double rotations in SO(4); line-weight aerial perspective for legible wireframes.
Self-check: `cd src && uv run python -m faces.vibes.tesseract`."""
import numpy as np

from ..primitives import frame, smoothstep
from ..spec import Vibe

_CX, _CY = 64, 32
_R = 27                                            # final on-screen radius scale
_DIVE = 1.8                                         # seconds for the eyes->tesseract transition
_GAP = 0.25                                         # a frame gap longer than this -> the vibe (re)started
_SPIN = 0.45                                        # angular velocity (rad/s) of the single x-w rotation

_V0 = np.array([(x, y, z, w) for x in (-1, 1) for y in (-1, 1)        # the 16 hypercube corners (Nx4)
                for z in (-1, 1) for w in (-1, 1)], float)
_EDGES = tuple((i, j) for i in range(16) for j in range(i + 1, 16)
               if int(((_V0[i] != _V0[j]).sum())) == 1)               # differ in one coord -> 32 edges

_WB = 1.6                                           # w-depth weight: the front cell reads as nearer in 4D
_BOLD = 0.55                                        # edges with mean nearness above this are drawn 2px (bold)


def _planerot(theta, i, k):
    """A 4x4 rotation by theta in the (i, k) coordinate plane -- one generator of SO(4)."""
    r = np.eye(4)
    c, s = np.cos(theta), np.sin(theta)
    r[i, i] = r[k, k] = c
    r[i, k], r[k, i] = -s, s
    return r


_VIEW = _planerot(0.52, 0, 2) @ _planerot(0.32, 1, 2)   # fixed 3/4 tilt -> the nested cubes stay legible

# Per-pixel dissolve order, precomputed once: outer eye pixels vanish first, the centre (where the
# cube is being born) holds longest -> the eyes look sucked into the fourth dimension.
_Y, _X = np.mgrid[0:64, 0:128]
_DIST = np.hypot(_X - _CX, _Y - _CY)
_DIST /= _DIST.max()
_THRESH = (1.0 - _DIST) * 0.6 + np.random.RandomState(7).random((64, 128)) * 0.4   # 0..1, erase when p>thresh

_st = {"t0": None, "last": -1.0}                   # dive start + last-frame clock


def _orient(t):
    return _VIEW @ _planerot(_SPIN * t, 0, 3)      # fixed view, then the single animated x-w rotation


def _project(V, grow):
    """Rotated 4D verts (Nx4) -> screen pts + per-vertex nearness T (1 = closest to the camera)."""
    x, y, z, w = V[:, 0], V[:, 1], V[:, 2], V[:, 3]
    d4 = 22.0 - 19.0 * grow                         # 22 (a far point) -> 3.0: the cube inflates out of 4D
    s4 = 2.2 / (d4 - w)                             # 4D -> 3D perspective divide
    x, y, z = x * s4, y * s4, z * s4
    s3 = 2.2 / (3.2 - z)                            # 3D -> 2D perspective divide
    pts = np.stack([_CX + x * s3 * _R, _CY + y * s3 * _R], axis=1)
    depth = _WB * (d4 - w) + (3.2 - z)              # camera distance: through 4D (weighted) then 3D
    rng = depth.max() - depth.min() or 1.0
    return pts, 1.0 - (depth - depth.min()) / rng   # 1 at the nearest corner, 0 at the farthest


def _draw_edges(d, pts, T):
    """Solid wireframe, far-to-near so the front cell overlays the back; near edges bold (2px)."""
    for i, j in sorted(_EDGES, key=lambda e: T[e[0]] + T[e[1]]):       # farthest edges first
        w = 2 if (T[i] + T[j]) * 0.5 > _BOLD else 1
        d.line([pts[i, 0], pts[i, 1], pts[j, 0], pts[j, 1]], fill=1, width=w)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    s = _st
    if s["last"] < 0 or now - s["last"] > _GAP:     # fresh activation -> restart the dive
        s["t0"] = now
    s["last"] = now
    p = (now - s["t0"]) / _DIVE
    grow = smoothstep(p)
    pts, T = _project(_V0 @ _orient(now - s["t0"]).T, grow)   # single x-w spin from the dive start

    img = frame(d)
    if p < 1.0 and img is not None:                 # mid-dive: dissolve the eyes outward-first
        eyes = np.asarray(img, dtype=bool) & (_THRESH > p)
        img.frombytes(np.packbits(eyes, axis=1).tobytes())
    else:                                           # dive done: the wireframe owns the screen
        d.rectangle([0, 0, W - 1, H - 1], fill=0)
    _draw_edges(d, pts, T)


VIBE = Vibe("tesseract", mood="awe", overlay=_overlay)


def _span(grow):
    pts, _ = _project(_V0, grow)
    return np.hypot(*(pts - (_CX, _CY)).T).max()


def _selfcheck():
    assert len(_EDGES) == 32, f"a tesseract has 32 edges, got {len(_EDGES)}"
    assert _span(0.0) < 4.0 < 20.0 < _span(1.0), "cube should unfold from a near-point to fill the screen"

    # --- the motion: a single SO(4) rotation -- proper, periodic, and only the x-w plane animates ---
    for t in (0.0, 1.3, 4.7):
        R = _orient(t)
        assert np.abs(R.T @ R - np.eye(4)).max() < 1e-9, "orientation must stay orthogonal (in O(4))"
        assert abs(np.linalg.det(R) - 1.0) < 1e-9, "orientation must be a proper rotation (det +1)"
    period = 2 * np.pi / _SPIN
    assert np.allclose(_orient(0.0), _orient(period)), "a simple rotation must be perfectly periodic"
    # only x(0) and w(3) move; the y(1)-z(2) sub-block is held fixed by the (non-animated) view
    base = _orient(0.0)[1:3, 1:3]
    assert np.allclose(_orient(2.0)[1:3, 1:3], base), "the y-z block must not rotate -> single-plane spin"

    # --- the depth cue: nearness spans [0,1], and a near edge is drawn bolder (more pixels) ---
    from PIL import Image, ImageDraw
    pts, T = _project(_V0 @ _orient(1.0).T, 1.0)
    assert 0.0 <= T.min() and T.max() <= 1.0 + 1e-9 and abs(T.max() - 1.0) < 1e-9, "T must be normalized nearness"
    assert T.max() - T.min() > 0.2, "depth cueing should give real near/far contrast"
    near, far = (Image.new("1", (128, 64), 0) for _ in range(2))
    i, j = max(_EDGES, key=lambda e: T[e[0]] + T[e[1]])              # nearest (bold) edge
    k, l = min(_EDGES, key=lambda e: T[e[0]] + T[e[1]])             # farthest (thin) edge
    ImageDraw.Draw(near).line([pts[i, 0], pts[i, 1], pts[j, 0], pts[j, 1]], fill=1, width=2)
    ImageDraw.Draw(far).line([pts[k, 0], pts[k, 1], pts[l, 0], pts[l, 1]], fill=1, width=1)
    if np.hypot(*(pts[i] - pts[j])) > 3 and np.hypot(*(pts[k] - pts[l])) > 3:
        assert np.asarray(near, bool).sum() > np.asarray(far, bool).sum(), "the near edge should be bolder"

    # --- the transition: eyes erode over the dive ---
    def _eyes_after(last):
        img = Image.new("1", (128, 64), 0)
        ImageDraw.Draw(img).ellipse([40, 22, 88, 42], fill=1)
        _st.update(t0=0.0, last=last)
        _overlay(ImageDraw.Draw(img), 128, 64, max(last, 0.0))
        return int(np.asarray(img, bool).sum())
    early, late = _eyes_after(-1.0), _eyes_after(_DIVE * 0.7)
    assert late < early, f"dissolve should erode the eyes over the dive ({early} -> {late} px)"
    print(f"tesseract ok: 32 edges, span {_span(0.0):.1f}->{_span(1.0):.1f}px | "
          f"single x-w rotation, period {period:.1f}s, depth contrast {T.max() - T.min():.2f}, "
          f"dissolve {early}->{late}px")


if __name__ == "__main__":
    _selfcheck()
