"""Conway's Game of Life -- Pip's eyes come alive. A B3/S23 cellular automaton seeds inside the
eyes and crawls outward: the play area is the *starting* eye footprint, captured once and grown a
few px, so the cells can spill a little beyond the eye outline while staying bounded. Capturing the
resting eye once (not the live, blinking one each frame) keeps the hand-off from eyes to life
smooth. Re-seeds whenever the board settles -- static or a short cycle -- after _STALE seconds.

CPU: 2px cells (a 64x32 board), the sim only advances on a new generation, and each frame writes the
1-bit panel back in place (no per-frame PIL image is built).
Self-check: `cd src && uv run python -m faces.vibes.game_of_life`."""
import numpy as np

from ..primitives import frame
from ..spec import Vibe

_PX = 2                                    # px per cell -- 1px reads too small
_COLS, _ROWS = 128 // _PX, 64 // _PX       # 64 x 32 board
_CELL = np.ones((_PX, _PX), np.uint8)      # a cell -> a 2x2 block
_STEP = 0.15                               # seconds per generation -- gentle, smooth evolution
_STALE = 10.0                              # re-seed after this long with no genuinely new state
_DENSITY = 0.32                            # live fraction of the seed soup
_GROW = 3                                  # cells the play area extends past the eye (so life spills out, bounded)
_MIN_EYE = 80                              # px: capture only once the eyes are open -> smooth hand-off
_HIST = 24                                 # generations kept to spot a repeat -- detects cycles up to this period
_MAX_CATCHUP = 4                           # cap generations advanced per frame (slow frame -> don't spiral)

_gol = {"grid": None, "area": None, "seedmask": None, "gen_t": 0.0, "fresh_t": 0.0, "hist": None, "seed": 0}


def _dilate(a, n):                         # grow a boolean mask by n cells (4-neighbour)
    for _ in range(n):
        a = a | np.roll(a, 1, 0) | np.roll(a, -1, 0) | np.roll(a, 1, 1) | np.roll(a, -1, 1)
    return a


def _capture(eye, now):
    """Lock the play area to the resting eyes (downsampled to cells), grown by _GROW so life spills out."""
    g = _gol
    g["seedmask"] = eye.reshape(_ROWS, _PX, _COLS, _PX).any(axis=(1, 3))   # a cell is on if any of its 2x2 px lit
    g["area"] = _dilate(g["seedmask"], _GROW)
    _seed(now)


def _seed(now):
    g = _gol
    np.random.seed(1234 + g["seed"])       # first soup fixed (stable showcase); each re-seed differs
    g["seed"] += 1
    g["grid"] = (np.random.random((_ROWS, _COLS)) < _DENSITY) & g["seedmask"]   # soup, born inside the eyes
    g["gen_t"] = g["fresh_t"] = now
    g["hist"] = [g["grid"].tobytes()]


def _step(grid):                           # B3/S23 with toroidal wrap (np.roll); pure -> testable
    nb = sum(np.roll(np.roll(grid, dy, 0), dx, 1)
             for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0))
    return (nb == 3) | (grid & (nb == 2))


def _advance(now):
    g = _gol
    if now < g["gen_t"]:                            # clock jumped back -> reseed in the same area
        _seed(now)
    steps = 0
    while now - g["gen_t"] >= _STEP and steps < _MAX_CATCHUP:
        nxt = _step(g["grid"]) & g["area"]          # contained: cells can fill the grown area, no further
        key = nxt.tobytes()
        if key not in g["hist"]:                    # a state we haven't seen lately -> the board is still alive
            g["fresh_t"] = g["gen_t"] + _STEP
        g["hist"].append(key)
        del g["hist"][:-_HIST]
        g["grid"] = nxt
        g["gen_t"] += _STEP
        steps += 1
    if now - g["fresh_t"] >= _STALE:                # settled (static or short cycle) too long -> reset
        _seed(now)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    g = _gol
    img = frame(d)
    if g["area"] is None:                           # first frames: capture the resting eyes ONCE, then own the frame
        if img is None:
            return
        eye = np.asarray(img, dtype=bool)
        if eye.sum() < _MIN_EYE:                    # eyes still opening (swap-blink) -> wait, smooth hand-off
            return
        _capture(eye, now)
    _advance(now)
    if img is None:
        return
    big = np.kron(g["grid"].astype(np.uint8), _CELL)           # board -> full-panel 2px-block bitmap
    img.frombytes(np.packbits(big, axis=1).tobytes())          # write the 1-bit panel back in place


VIBE = Vibe("game_of_life", mood="neutral", overlay=_overlay)


def _reset_state():
    _gol.update(grid=None, area=None, seedmask=None, gen_t=0.0, fresh_t=0.0, hist=None, seed=0)


def _selfcheck():
    from PIL import Image, ImageDraw

    blink = np.zeros((5, 5), bool); blink[2, 1:4] = True                 # blinker -> period-2 oscillator
    after = _step(blink)
    assert after[1:4, 2].all() and not after[2, 1] and not after[2, 3], "blinker should flip vertical"
    assert np.array_equal(_step(after), blink), "blinker should return after 2 gens"

    block = np.zeros((4, 4), bool); block[1:3, 1:3] = True               # 2x2 block -> still life
    assert np.array_equal(_step(block), block), "block should be stable"

    g = np.zeros((16, 16), bool)                                         # glider -> moves (+1,+1) every 4 gens
    for r, c in [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]:
        g[r, c] = True
    g4 = g
    for _ in range(4):
        g4 = _step(g4)
    assert np.array_equal(g4, np.roll(np.roll(g, 1, 0), 1, 1)), "glider should translate by (1,1) per 4 gens"

    img = Image.new("1", (128, 64), 0)                                   # capture + render round-trip on a fake eye
    ImageDraw.Draw(img).ellipse([38, 22, 60, 42], fill=1)
    _reset_state()
    _overlay(ImageDraw.Draw(img), 128, 64, 0.0)                          # frame 0: captures the eye, seeds, draws
    assert _gol["area"] is not None, "eye never captured"
    assert (_gol["area"] & ~_gol["seedmask"]).any(), "area should extend beyond the eye (dilation)"
    assert not (_gol["seedmask"] & ~_gol["area"]).any(), "the eye must lie inside its grown area"
    assert np.asarray(img, bool).sum() > 0, "nothing drawn"

    for _ in range(30):                                                  # containment: cells never escape the area
        _gol["grid"] = _step(_gol["grid"]) & _gol["area"]
    assert not (_gol["grid"] & ~_gol["area"]).any(), "life leaked outside the bounded area"

    class _Stub:                                                         # drive the stale-reset path headlessly
        _image = None
    _gol["grid"][:] = False                                             # an empty board is settled -> must reset
    _gol["hist"] = [_gol["grid"].tobytes()]
    _gol["gen_t"] = _gol["fresh_t"] = 0.0
    s0 = _gol["seed"]
    for i in range(1, 40):
        _overlay(_Stub(), 128, 64, i * 0.5)
    assert _gol["seed"] > s0, "a settled board never reset"
    print(f"game_of_life ok: blinker p2, block stable, glider moves, eye->area capture + spill, re-seed {s0}->{_gol['seed']}")


if __name__ == "__main__":
    _selfcheck()
