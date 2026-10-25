"""Quantum -- Pip's eyes literally become a wavefunction. We integrate the time-dependent Schrodinger
equation  i dpsi/dt = -1/2 nabla^2 psi + V psi  (hbar=m=1) by the SPLIT-STEP FOURIER method: a half
potential kick, a full kinetic drift done exactly in k-space (psi_hat *= e^{-i k^2 dt/2}), then
another half kick. It is unitary -- |psi|^2 conserved to machine precision -- and spectrally exact,
so the only physics is the equation; the sloshing and interference EMERGE.

Smooth hand-off: the eye fill IS the initial amplitude, so at t=0 |psi|^2 equals the solid eye and
the eye seamlessly turns into a probability cloud. A momentum kick sends it sloshing; each eye is a
soft-walled infinite well (the captured footprint, grown _GROW px) so the packet bounces and
interferes with its reflections. A finite well never disperses to a flat haze, so it stays lively
forever -- no relaunch. |psi|^2 is ordered-dithered to 1-bit at 2px.

CPU: two FFTs per substep on a 128x64 grid (microseconds), a few substeps per frame, written back in
place. Self-check: `cd src && uv run python -m faces.vibes.quantum`."""
import numpy as np

from ..primitives import frame
from ..spec import Vibe

NX, NY = 128, 64                           # wavefunction grid == panel
_PX = 2                                    # display cell -> a 2x2 block (1px reads too small)
_CELL = np.ones((_PX, _PX), np.uint8)
_DT = 0.15                                 # split-step time step (sim-s) -- both phases stay < pi, fully resolved
_SPEED = 10.0                              # sim-seconds per wall-second
_MAX_SUB = 12                              # substep cap per frame (slow frame -> don't spiral)
_V0 = 20.0                                 # well-wall height (>> packet KE -> confinement)
_K0 = 1.2                                  # initial momentum kick -> the eye-cloud sloshes
_GROW = 5                                  # px the well extends past the eye (cloud spills out, bounded)
_GAMMA = 0.75                              # brighten faint probability before dithering (keeps tails dark)
_MIN_EYE = 80                              # px: capture only once the eyes are open -> smooth hand-off

_X, _Y = np.meshgrid(np.arange(NX), np.arange(NY))                    # pixel coords (NY, NX)
_KX, _KY = np.meshgrid(2 * np.pi * np.fft.fftfreq(NX), 2 * np.pi * np.fft.fftfreq(NY))
_EXPK = np.exp(-1j * 0.5 * (_KX ** 2 + _KY ** 2) * _DT)               # exact kinetic propagator (k-space)
_BAYER = np.tile((np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 1) / 17.0,
                 (NY // _PX // 4, NX // _PX // 4))                    # 4x4 ordered-dither (floored >0 so faint density stays dark)

_q = {"psi": None, "eye": None, "area": None, "area_cells": None, "expV": None, "wall": 0.0}


def _dilate(a, n):                         # grow a boolean mask by n px (4-neighbour)
    for _ in range(n):
        a = a | np.roll(a, 1, 0) | np.roll(a, -1, 0) | np.roll(a, 1, 1) | np.roll(a, -1, 1)
    return a


def _blur(a, n):                           # box-smooth a field n times
    for _ in range(n):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5.0
    return a


def _launch(now):
    """Seed the wavefunction FROM the eyes: amplitude = the eye fill (so t=0 density == the solid eye),
    times a per-eye momentum phase that sends each cloud sloshing."""
    q = _q
    np.random.seed(777)                                # deterministic headings -> stable showcase
    amp = _blur(q["eye"].astype(float), 1)             # softened eye edge -> less high-k reflection ringing
    psi = np.zeros((NY, NX), complex)
    for half in (_X < NX / 2, _X >= NX / 2):           # left eye, right eye -- own heading each
        ang = np.random.uniform(0, 2 * np.pi)
        psi += amp * half * np.exp(1j * (_K0 * np.cos(ang) * _X + _K0 * np.sin(ang) * _Y))
    norm = np.sqrt((np.abs(psi) ** 2).sum())
    if norm > 0:
        psi /= norm
    q["psi"], q["wall"] = psi, now


def _capture(eye, now):
    """Lock the well to the resting eyes (grown by _GROW), build the soft wall, seed from the eyes."""
    q = _q
    q["eye"] = eye
    q["area"] = _dilate(eye, _GROW)
    q["area_cells"] = q["area"].reshape(NY // _PX, _PX, NX // _PX, _PX).any(axis=(1, 3))
    wall = _blur((~q["area"]).astype(float), 2)        # 0 inside, ramps to 1 just outside -> soft well wall
    q["expV"] = np.exp(-1j * _V0 * wall * (_DT / 2))   # half-step potential propagator
    _launch(now)


def _split_step():                         # one unitary split-step: half kick, exact kinetic drift, half kick
    q = _q
    p = q["psi"] * q["expV"]
    p = np.fft.ifft2(_EXPK * np.fft.fft2(p))
    q["psi"] = p * q["expV"]


def _advance(now):
    q = _q
    dtw = now - q["wall"]
    q["wall"] = now
    if dtw <= 0 or dtw > 0.25:                          # first frame / stall -> assume one tick
        dtw = 1.0 / 30.0
    for _ in range(min(_MAX_SUB, max(1, round(_SPEED * dtw / _DT)))):
        _split_step()


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    q = _q
    img = frame(d)
    if q["psi"] is None:                                # first frames: capture the resting eyes ONCE
        if img is None:
            return
        eye = np.asarray(img, dtype=bool)
        if eye.sum() < _MIN_EYE:                        # eyes still opening (swap-blink) -> wait, smooth hand-off
            return
        _capture(eye, now)
    _advance(now)
    if img is None:
        return
    dens = np.abs(q["psi"]) ** 2                                          # probability density
    small = dens.reshape(NY // _PX, _PX, NX // _PX, _PX).mean(axis=(1, 3))   # -> 2px display grid
    mx = small.max()
    if mx > 0:
        small = (small / mx) ** _GAMMA
    lit = (small > _BAYER) & q["area_cells"]                             # ordered-dither, clipped to the well
    img.frombytes(np.packbits(np.kron(lit.astype(np.uint8), _CELL), axis=1).tobytes())


VIBE = Vibe("quantum", mood="neutral", overlay=_overlay)


def _reset_state():
    _q.update(psi=None, eye=None, area=None, area_cells=None, expV=None, wall=0.0)


def _selfcheck():
    from PIL import Image, ImageDraw

    # 1. free particle: unitarity (|psi|^2 conserved) + Ehrenfest group velocity  d<x>/dt = k
    sig = 4.0
    psi = (np.exp(-(((_X - 30) ** 2 + (_Y - 32) ** 2) / (2 * sig ** 2))) * np.exp(1j * _K0 * _X)).astype(complex)
    psi /= np.sqrt((np.abs(psi) ** 2).sum())
    n0 = (np.abs(psi) ** 2).sum()
    x0 = (_X * np.abs(psi) ** 2).sum()
    steps = 40
    for _ in range(steps):                              # free evolution: kinetic only (V=0)
        psi = np.fft.ifft2(_EXPK * np.fft.fft2(psi))
    n1 = (np.abs(psi) ** 2).sum()
    disp, expected = (_X * np.abs(psi) ** 2).sum() - x0, _K0 * _DT * steps
    assert abs(n1 - n0) < 1e-9, f"norm not conserved ({n1 - n0:.1e}) -- evolution is not unitary"
    assert abs(disp - expected) < 0.05 * expected, f"group velocity wrong: <x> moved {disp:.2f}, expected {expected:.2f}"

    # 2. smooth seed: t=0 density == the eye fill, then it stays normalised, confined, and evolves
    img = Image.new("1", (128, 64), 0)
    ImageDraw.Draw(img).ellipse([34, 22, 58, 42], fill=1)
    ImageDraw.Draw(img).ellipse([70, 22, 94, 42], fill=1)               # two fake eyes
    _reset_state()
    _capture(eye := np.asarray(img, bool), 0.0)                         # seed only (no stepping) -> the t=0 state
    d0 = np.abs(_q["psi"]) ** 2
    inside = d0[eye]
    assert inside.min() > 0 and inside.std() / inside.mean() < 0.25, "t=0 density should match the (uniform) eye fill"
    assert abs(d0[~_q["area"]].sum()) < 1e-9, "no amplitude should start outside the well"
    for i in range(1, 40):
        _overlay(ImageDraw.Draw(img), 128, 64, i / 30.0)
    d1 = np.abs(_q["psi"]) ** 2
    assert abs(d1.sum() - 1.0) < 1e-6, "norm drifted in the well"
    assert (d1 * _q["area"]).sum() > 0.85, "wavepacket leaked out of the well"
    assert np.abs(d1 - d0).sum() > 0.05, "wavefunction never evolved"
    print(f"quantum ok: unitary (dN={n1 - n0:.0e}), <x> moved {disp:.1f}~{expected:.1f}, "
          f"t0==eye, confined {(d1 * _q['area']).sum():.2f}, evolving")


if __name__ == "__main__":
    _selfcheck()
