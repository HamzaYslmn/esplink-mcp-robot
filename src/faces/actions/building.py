"""Building -- a little 3D voxel build on a turntable under Pip's eyes. Shaded cubes (lit tops, dotted
sides, dark shadow faces, one crisp outline) drop from above, fall under gravity, land with a bounce
and a puff of dust, and stack layer by layer into something -- a house, a tree, a tower, a rocket,
a pyramid, an arch, a little robot -- the whole build slowly turning the while.

Every build plays out its own way:
  slam    a whole layer drops in at once -- the ground shakes, the build hops
  miss    a cube lands on an edge, teeters, slides off and tumbles away; a fresh one drops in
  whirl   the turntable whips round a full turn mid-build, Pip's eyes swept along
When it's done it spins round in triumph under a sparkle -- then blows apart, cubes flying out and
tumbling away, and the next build starts dropping in.

Self-check: `cd src && uv run python -m faces.actions.building`."""
import math
from functools import cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from ..painters import brow, lids
from ..primitives import flip, frame, halftone, rand, smoothstep
from ..spec import Action

_BUILD = 10.0                   # s per build
_S = 7                         # px per cube
_SS = 4                        # supersample factor
_BASE = (64, 61)               # where the turntable's centre sits on screen
_FALL, _DROP = 0.32, 22.0      # s a cube falls, from how high (px)
_BOUNCE = 0.14                 # s of the landing hop
_SPIN = 1.3                    # s the finished build spins round in triumph
_BLAST = 1.0                   # s the build takes to blow apart
_TURN = 0.8                    # rad/s the turntable idles at
_THINGS = {                    # voxel builds: layers bottom-up, rows of a layer are depth, '#' a cube
    "house": ("###/###/###", "###/###/###", "   /###/   "),
    "tree": ("   / # /   ", "   / # /   ", "###/###/###", " # /###/ # ", "   / # /   "),
    "tower": ("###/###/###", "###/###/###", "###/###/###", "# #/   /# #"),
    "rocket": (" # /###/ # ", " # ", " # ", " # ", " # "),
    "pyramid": ("####/####/####/####", "    / ## / ## /    ", "    /  # /    /    "),
    "arch": ("# #", "# #", "###"),
    "robot": ("# #", "###", "###", " # "),
}


# -- the plan ------------------------------------------------------------------------------------------
def _voxels(name):
    """[(i, j, k)] cubes of a build, centred on the turntable's axis."""
    vox = [(i, j, k) for k, layer in enumerate(_THINGS[name]) for j, row in enumerate(layer.split("/"))
           for i, ch in enumerate(row) if ch == "#"]
    ci = (max(v[0] for v in vox) + min(v[0] for v in vox)) / 2
    cj = (max(v[1] for v in vox) + min(v[1] for v in vox)) / 2
    return [(i - ci, j - cj, k) for i, j, k in vox]


@cache
def _plan(s):
    """-> (cubes [(i, j, k)] in drop order, landing times, slam layer | None, miss index | None,
    whirl time | None, finished time). Cubes go down layer by layer, in a random order in each."""
    names = sorted(_THINGS)
    vox = _voxels(names[int(rand(s, 1) * len(names))])
    vox.sort(key=lambda v: (v[2], rand(s, v[0], v[1], v[2])))
    layers = max(v[2] for v in vox) + 1
    slam = int(rand(s, 2) * layers) if rand(s, 3) < 0.45 else None
    miss = int(rand(s, 4) * (len(vox) - 1)) + 1 if rand(s, 5) < 0.4 else None
    lands, t = [], 0.3 + _FALL
    budget = 4.8 / len(vox)                                 # every build takes about as long
    for n, v in enumerate(vox):
        if slam is not None and v[2] == slam and n and vox[n - 1][2] == slam:
            lands.append(lands[-1])                         # the slammed layer all lands together
            continue
        if n:
            t += budget * (0.6 + 0.8 * rand(s, n, 6)) + (0.5 if slam is not None and v[2] == slam else 0)
        if n == miss:
            t += 0.9                                        # the one that slid off: its replacement's late
        lands.append(t)
    last = _BUILD - 0.25 - _BLAST - 0.15 - _SPIN - 0.2 - _BOUNCE   # stretch the pace to fill the slot: no dead air
    if len(lands) > 1 and lands[-1] > lands[0]:
        k = (last - lands[0]) / (lands[-1] - lands[0])
        lands = [lands[0] + (at - lands[0]) * k for at in lands]
    whirl = 0.4 + rand(s, 7) * (lands[-1] - 1.5) if rand(s, 8) < 0.35 else None
    return tuple(vox), tuple(lands), slam, miss, whirl, lands[-1] + _BOUNCE + 0.2


def _build(now):
    T, seed = getattr(now, "t", now), getattr(now, "seed", 0)
    k, t = divmod(T, _BUILD)
    return T, t, _plan(int(rand(seed, k) * 1e6))


def _angle(T, t, plan):
    """The turntable: idling round, whipped a full turn by a whirl, spun in triumph when done."""
    _, _, _, _, whirl, done = plan
    a = _TURN * T
    if whirl is not None:
        a += math.tau * smoothstep((t - whirl) / 0.8)
    a += math.tau * smoothstep((t - done) / _SPIN)
    return a


def _cubes(t, plan):
    """[(x, y, z) world px, rot] of every cube on show -- falling, bouncing, sliding off, settled, or
    flying apart -- y up from the turntable."""
    vox, lands, slam, miss, whirl, done = plan
    out = []
    blast = t - done - _SPIN - 0.15
    for n, (i, j, k) in enumerate(vox):
        x, y, z = i * _S, k * _S, j * _S
        u = t - lands[n]
        if u < -_FALL:
            continue
        if u < 0:                                           # falling: accelerating down from above
            y += _DROP * (u / _FALL) ** 2
        elif u < _BOUNCE:                                   # a little hop on landing
            y += 2.5 * math.sin(math.pi * u / _BOUNCE) * (0.5 if slam is not None and k == slam else 1)
        if blast > 0:                                       # blown apart: out, up, tumbling, gone
            r = math.hypot(i, j) + 0.5
            vx, vz = (i or rand(n, 1) - 0.5) / r * 85, (j or rand(n, 2) - 0.5) / r * 85
            vy = 22 + 18 * rand(n, 3) + 3 * k                   # up a little, mostly out
            x, z = x + vx * blast, z + vz * blast
            y += vy * blast - 160 * blast * blast
        out.append((x, y, z))
    if miss is not None:                                    # the one that slid off the edge
        u = t - (lands[miss] - 0.9)
        if -_FALL <= u < 1.0:
            i, j, k = vox[miss]
            edge = 1 if i >= 0 else -1
            x, y, z = (i + edge * 0.5) * _S, k * _S, j * _S
            if u < 0:
                y += _DROP * (u / _FALL) ** 2
            elif u < 0.35:                                  # teeters on the edge
                x += math.sin(u * 40) * 1.2
            else:                                           # slides off and tumbles away
                w = u - 0.35
                x += edge * 30 * w
                y -= 120 * w * w
            out.append((x, y, z))
    return out


# -- drawing -------------------------------------------------------------------------------------------
def _faces(x, y, z, th):
    """The visible faces of one cube at world (x, y, z), turned th: [(screen quad, grey)] -- shadow
    sides dark, lit sides light, the top white."""
    c, sn = math.cos(th), math.sin(th)

    def P(px, py, pz):
        rx, rz = px * c - pz * sn, px * sn + pz * c
        return (_BASE[0] + rx) * _SS, (_BASE[1] - py * 0.85 + rz * 0.42) * _SS

    h, s = _S / 2, _S
    out = []
    for nx, nz, a, b in ((1, 0, (h, -h), (h, h)), (-1, 0, (-h, h), (-h, -h)), (0, 1, (h, h), (-h, h)), (0, -1, (-h, -h), (h, -h))):
        if nx * sn + nz * c > 0.01:                         # facing us
            light = 0.5 + 0.5 * (nx * c - nz * sn)          # lit from the left-front
            out.append(([P(x + a[0], y, z + a[1]), P(x + b[0], y, z + b[1]),
                         P(x + b[0], y + s, z + b[1]), P(x + a[0], y + s, z + a[1])], round(30 + 120 * light)))
    out.append(([P(x - h, y + s, z - h), P(x + h, y + s, z - h), P(x + h, y + s, z + h), P(x - h, y + s, z + h)], 255))
    return out


def _render(img, W, H, cubes, th):
    """Paint the cubes back to front in greys, halftone them, and outline the whole silhouette."""
    art, mask = Image.new("L", (W * _SS, H * _SS)), Image.new("L", (W * _SS, H * _SS))
    a, m = ImageDraw.Draw(art), ImageDraw.Draw(mask)
    c, sn = math.cos(th), math.sin(th)
    for x, y, z in sorted(cubes, key=lambda q: (q[1] // _S, q[0] * sn + q[2] * c, q[1])):
        for quad, g in _faces(x, y, z, th):
            a.polygon(quad, fill=g, outline=0 if g == 255 else None, width=_SS // 2)
            m.polygon(quad, fill=255)
    grey = art.resize((W, H), Image.BOX)
    cover = mask.resize((W, H), Image.BOX).point(lambda v: 255 if v >= 100 else 0)
    rim = cover.filter(ImageFilter.MaxFilter(3))
    img.paste(1, (0, 0), ImageChops.subtract(rim, cover).convert("1"))   # a lit outline round it all
    img.paste(0, (0, 0), cover.convert("1"))
    img.paste(1, (0, 0), ImageChops.multiply(halftone(grey).convert("L"), cover).convert("1"))


def _screen(x, y, z, th):
    c, sn = math.cos(th), math.sin(th)
    return _BASE[0] + x * c - z * sn, _BASE[1] - y * 0.85 + (x * sn + z * c) * 0.42


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    img = frame(d)
    if img is None:
        return
    T, t, plan = _build(now)
    vox, lands, slam, miss, whirl, done = plan
    th = _angle(T, t, plan)
    hop = 0.0
    if slam is not None:                                    # the slammed layer jolts the whole build
        at = next(lands[n] for n, v in enumerate(vox) if v[2] == slam)
        u = t - at
        if 0 <= u < 0.25:
            hop = 3 * math.sin(math.pi * u / 0.25)
    cubes = [(x, y + hop, z) for x, y, z in _cubes(t, plan)]
    if cubes:
        _render(img, W, H, cubes, th)
    for n, (i, j, k) in enumerate(vox):                     # dust puffing out under each landing
        u = t - lands[n]
        if 0 <= u < 0.22 and t < done + _SPIN:
            sx, sy = _screen(i * _S, k * _S, j * _S, th)
            for side in (-1, 1):
                flip(d, sx + side * (5 + 14 * u), sy + 3 - 6 * u)
    if done + 0.3 < t < done + _SPIN:                       # a sparkle over the finished build
        f = (t - done - 0.3) / (_SPIN - 0.3)
        r = round(3 * math.sin(math.pi * f))
        top = max(v[2] for v in vox) + 1
        sx, sy = _BASE[0] + 12, _BASE[1] - top * _S * 0.85 - 6
        for k in range(1, r + 1):
            for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
                flip(d, sx + dx, sy + dy)
    if slam is not None:                                    # ...and shakes the screen
        at = next(lands[n] for n, v in enumerate(vox) if v[2] == slam)
        if 0 <= t - at < 0.1:
            snap = img.copy()
            d.rectangle([0, 0, W - 1, H - 1], fill=0)
            img.paste(snap, (0, 2 if int((t - at) * 60) % 2 else -1))


def _pose(now):   # eyes up out of the build's way; watch each cube land; swept by a whirl
    T, t, plan = _build(now)
    vox, lands, slam, miss, whirl, done = plan
    gx, gy, h = math.sin(now * 0.6) * 1.5, -11.0, 0.72
    falling = [n for n in range(len(vox)) if -_FALL <= t - lands[n] < 0.15]
    if falling:                                             # glance at where the newest one lands
        i, j, k = vox[falling[-1]]
        sx, _ = _screen(i * _S, k * _S, j * _S, _angle(T, t, plan))
        gx = (sx - 64) * 0.25
        if t - lands[falling[-1]] >= 0:
            gy += 1.5 * math.sin(math.pi * (t - lands[falling[-1]]) / 0.15)
    if whirl is not None and whirl <= t < whirl + 0.8:      # swept round with it
        gx += 5 * math.sin(math.tau * (t - whirl) / 0.8)
    if t > done + _SPIN + 0.15:                             # it blows apart: a flinch
        u = t - done - _SPIN - 0.15
        h -= 0.2 * math.sin(math.pi * min(1.0, u / 0.4))
    return gx, gy, h


def _focus(t, plan):
    """0..1 a moment of concentration: a quick pinch as a slammed layer or the last cube goes in, a
    longer one while a cube teeters on the edge -- plain open eyes the rest of the time."""
    vox, lands, slam, miss, whirl, done = plan
    beats = [(lands[-1], 0.5)]                              # the final piece
    if slam is not None:
        beats.append((next(lands[n] for n, v in enumerate(vox) if v[2] == slam) - 0.3, 0.7))
    if miss is not None:
        beats.append((lands[miss] - 0.9, 1.0))              # watching it teeter
    return max((math.sin(math.pi * (t - at) / dur) for at, dur in beats if 0 <= t - at < dur), default=0.0)


def _eyes(d, x, y, w, h, right, now):
    """Pip's own plain eyes, only now and then narrowing -- a top lid tipping in toward the nose, a
    lower lid riding up -- in a moment of real concentration, then opening right back up."""
    k = _focus(_build(now)[1], _build(now)[2])
    if k > 0.02:
        brow(d, x, y, w, h, 0.28 * k, 0.08 * k, right)
        lids(d, x, y, w, h, bottom=1 - 0.16 * k)


ACTION = Action("building", mood="neutral", pose=_pose, overlay=_overlay, eyes=_eyes)


if __name__ == "__main__":
    seen, events = set(), {"slam": False, "miss": False, "whirl": False}
    for s in range(300):
        plan = _plan(s)
        vox, lands, slam, miss, whirl, done = plan
        seen.add(tuple(sorted(vox)))
        assert all(a <= b for a, b in zip(lands, lands[1:])), "cubes land in order"
        assert [v[2] for v in vox] == sorted(v[2] for v in vox), "layer by layer, bottom up"
        assert done + _SPIN + 0.15 + _BLAST <= _BUILD, f"each build blows apart inside its slot: {done:.2f}"
        assert lands[0] - _FALL >= 0.25, "the first cube drops after the last build's gone"
        final = _cubes(done + 0.5, plan)
        assert len(final) == len(vox) and all(abs(c[1] - v[2] * _S) < 1e-9 for c, v in zip(final, vox)), "all home"
        gone = _cubes(_BUILD - 0.01, plan)
        assert all(_screen(*c, 0)[1] > 64 + 20 or c[1] < -40 or abs(c[0]) > 120 or abs(c[2]) > 120 for c in gone), "blown clear"
        events["slam"] |= slam is not None
        events["miss"] |= miss is not None
        events["whirl"] |= whirl is not None
    assert len(seen) == len(_THINGS) and all(events.values()), (seen, events)
    print("building ok")
