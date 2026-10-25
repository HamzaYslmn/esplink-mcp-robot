"""Searching -- Pip hunting for its cat in the dark, with a flashlight. The panel is a dark room;
a pool of light (crisp, with a soft dithered rim) glides slowly along the walls either side of Pip's
eyes -- hugging the wall, or arcing round over or under the eyes to cross the room -- and only what
the light falls on can be seen. At each spot it doesn't just stop: it circles, searching, and
spirals in onto whatever is there, so things are discovered as the light finds them. The eyes
follow the light, a touch ahead of it.

Each search is a short story of stops, always ending with the find. A stop can be:
  * empty   -- nothing there: the light circles and circles... and moves on;
  * junk    -- some random thing (every one generated, never the same twice): Pip leans in,
               squints, a little "nope" shake;
  * hmm     -- the light wanders aimlessly while Pip looks up, a "?" riding along with it;
  * sweep   -- the light runs down the wall and back, the eyes following it;
  * recheck -- the light starts to leave, then snaps back for a second, squinting look;
  * eyes    -- two glowing eyes blink in the dark on the far wall -- the cat! Pip startles, the
               light whips over, catches it for a blink... and it bolts, leaving a "?";
  * dim     -- the batteries sag: the light goes thin and wobbly while Pip shakes the flashlight,
               then it pops back bright;
  * fake    -- something shiny! a "!"... just a coin. The eyes droop;
  * found   -- the cat, there all along, blinking back at Pip, an ear twitching! The light holds,
               it glints, a "!" pops and Pip's face lights up.
On top of any stop the light can flicker off and on, and Pip blinks. Light and finds slip behind the
eyes with a pixel of dark margin. The room is littered with more random things the light catches as it
glides past. Every figure is generated: a mirrored blob of pixels, like an identicon. Stateless: every
search, stop and object is hashed off the clock."""
import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

from ..primitives import frame, rand, smoothstep
from ..spec import Action

_W, _H = 128, 64
_clock = [0.0]                                    # last frame's time, for the mood property
_CYCLE = 17.0                                     # s per search
_HOLD = {"empty": 1.5, "junk": 2.0, "hmm": 2.0, "sweep": 2.4, "recheck": 2.0, "eyes": 2.3,
         "dim": 2.2, "fake": 2.0, "found": 3.0}   # s each kind of stop is held (before fit)
_PICK = (("empty", 0.18), ("junk", 0.2), ("hmm", 0.1), ("sweep", 0.12), ("recheck", 0.1),
         ("eyes", 0.1), ("dim", 0.08), ("fake", 0.12))
_SPOTS = ((9, 12), (9, 32), (9, 52), (118, 12), (118, 32), (118, 52))   # the walls either side of the eyes
_R = 8                                            # light radius
_CLOSE = 1.0                                      # s the light takes to spiral in onto a thing
_LITTER = 7                                       # random things scattered on the walls per search
_BAYER = np.array(((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))) / 16 + 1 / 32
_DITHER = np.tile(_BAYER, (_H // 4, _W // 4))
_YY, _XX = np.mgrid[0:_H, 0:_W]


def _pick(c, i, last):
    for tries in range(4):                        # no kind twice running
        u = rand(c, 2, i, tries)
        for k, p in _PICK:
            if u < p:
                break
            u -= p
        if k != last:
            return k
    return "junk" if last == "empty" else "empty"


@lru_cache(maxsize=4)
def _story(c):
    """[(start, end, kind, spot, travel s, junk item)] for search c: 4-5 stops, the last the find."""
    n = 4 + int(rand(c, 1) * 2)
    kinds = []
    for i in range(n - 1):
        kinds.append(_pick(c, i, kinds[-1] if kinds else None))
    kinds.append("found")
    spots, s = [], int(rand(c, 3) * 6)
    for i in range(n):
        if kinds[i] == "eyes":                    # the cat is always on the other wall
            last = _SPOTS.index(spots[-1]) if spots else s
            s = (3 if last < 3 else 0) + int(rand(c, 8, i) * 3)
        spots.append(_SPOTS[s])
        s = (s + 1 + int(rand(c, 4, i) * 5)) % 6  # never the same spot twice running
    cross = [i == 0 or (spots[i - 1][0] < 64) != (spots[i][0] < 64) for i in range(n)]   # the first may cross
    travel = [(1.6 + 0.4 * rand(c, 9, i)) if cross[i] else (0.9 + 0.3 * rand(c, 9, i)) for i in range(n)]
    fit = (_CYCLE - sum(travel) - _HOLD["found"]) / sum(_HOLD[k] for k in kinds[:-1])   # the find keeps its time
    out, t = [], 0.0
    for i, k in enumerate(kinds):
        end = t + travel[i] + _HOLD[k] * (1.0 if k == "found" else fit)
        out.append((t, end, k, spots[i], travel[i], (c, 5, i)))   # last: the seed of its random thing
        t = end
    return tuple(out)


def _stop(now):
    """(search, stop index, the stop, seconds into it)."""
    c, t = int(now / _CYCLE), now % _CYCLE
    st = _story(c)
    i = next((i for i, s in enumerate(st) if t < s[1]), len(st) - 1)
    return c, i, st[i], t - st[i][0]


def _prev_spot(c, i):
    return _story(c)[i - 1][3] if i else _story(c - 1)[-1][3]


def _glide(u):                                    # ease in and out: a smooth, unhurried swing
    return 0.5 - 0.5 * math.cos(math.pi * min(1.0, max(0.0, u)))


def _path(p, q, e):
    """e of the way from wall spot p to q: bowing out along the wall, or arcing round over/under
    the eyes to cross the room (a quadratic curve through a control point)."""
    (px, py), (qx, qy) = p, q
    if (px < 64) == (qx < 64):
        cx, cy = px + (-5 if px < 64 else 5), (py + qy) / 2
    else:
        cx, cy = 64, (-8 if py + qy < 64 else 72)
    w0, w1, w2 = (1 - e) ** 2, 2 * (1 - e) * e, e * e
    return w0 * px + w1 * cx + w2 * qx, w0 * py + w1 * cy + w2 * qy


def _light(now):
    """(x, y, radius, brightness: 0 off / 1 dim / 2 full)."""
    c, i, (t0, t1, kind, (sx, sy), tr, _), u = _stop(now)
    hold = t1 - t0 - tr
    prev = _prev_spot(c, i)
    if kind == "eyes":                            # the light waits, then swings over to the eyes
        e = _glide((u - 0.7) / 0.45)
    else:
        e = _glide(u / tr)
    x, y = _path(prev, (sx, sy), e)
    r, lvl, h = _R, 2, u - (1.15 if kind == "eyes" else tr)
    if h > 0:
        ramp = _glide(h / 0.5) * _glide((hold - h) / 0.5)   # ease into the search pattern and back out of it
        if kind in ("empty", "junk", "fake", "found"):   # circle the spot, spiralling in on a find
            close = 1.0 if kind == "empty" else 1 - _glide(h / _CLOSE)
            a = h * 2.0
            x += ramp * close * 5.0 * math.sin(a)
            y += ramp * close * 3.5 * (1 - math.cos(a)) * (1 if sy < 32 else -1)
        elif kind == "hmm":                       # wandering, not really looking
            x += 5 * math.sin(h * 1.1) * ramp
            y += 3 * math.sin(h * 1.6) * ramp
        elif kind == "sweep":                     # down the wall and back, slowly
            y += ((52 if sy < 40 else 12) - sy) * (0.5 - 0.5 * math.cos(2 * math.pi * min(1.0, h / hold)))
        elif kind == "recheck" and 0.3 < h / hold < 0.8:   # starts to leave... comes back
            other = _SPOTS[(_SPOTS.index((sx, sy)) + 3) % 6]
            x, y = _path((sx, sy), other, math.sin(math.pi * (h / hold - 0.3) / 0.5) * 0.25)
        elif kind == "dim":
            f = h / hold
            if 0.15 < f < 0.75:                   # batteries sag; Pip shakes the flashlight
                lvl, r = 1, _R - 1
                if f > 0.4:
                    x += 1.5 * math.sin(now * 18)
                    y += 1.2 * math.sin(now * 15)
            elif 0.75 <= f < 0.85:
                r = _R + 1                        # and it comes back bright
    if kind == "found":                           # found: the light widens onto the cat
        r += 2 * _glide((h - _CLOSE + 0.3) / 0.5)
    x += 0.35 * math.sin(now * 2.1)               # a slow hand-held drift
    y += 0.3 * math.sin(now * 2.7)
    flick = rand(c, 6) < 0.45 and i == int(rand(c, 7) * (len(_story(c)) - 1))
    if flick and tr + 0.3 < u < tr + 0.65 and int((u - tr) * 14) % 3 != 2:
        lvl = 0
    return x, y, r, lvl


def _pose(now):
    _clock[0] = now
    c, i, (t0, t1, kind, (sx, sy), tr, _), u = _stop(now)
    hold, h = t1 - t0 - tr, u - tr
    lx, ly, _, lvl = _light(now + 0.25)           # the eyes follow the light, a touch ahead of it
    gx, gy = (lx - 64) * 0.08, (ly - 32) * 0.12
    if _light(now)[3] == 0:
        return gx, gy, 0.15                       # the light died: blink
    if kind == "eyes":
        if u < 0.25:
            return gx, gy, 0.85
        sgx, sgy = (sx - 64) * 0.08, (sy - 32) * 0.12
        if u < 1.6:                               # startled: wide, a nervous tremble, staring at them
            return sgx + 0.6 * math.sin(now * 30), sgy, 1.12
        return gx, gy, 0.65                       # ...gone. huh?
    if h < 0:
        return gx, gy, 0.85
    if kind == "junk":                            # lean in, squint... nope
        sq = 1.0 - 0.4 * smoothstep(min(1.0, max(0.0, (h - _CLOSE) / 0.3)))
        shake = 2.0 * math.sin(h * 22) if h > hold - 0.45 else 0.0
        return gx + shake, gy, sq
    if kind == "hmm":                             # look up and away, thinking
        return -gx * 0.6, -6.0, 0.8
    if kind == "recheck":
        return gx, gy, 0.6 if 0.3 < h / hold < 0.9 else 0.85
    if kind == "dim":
        return gx, gy, 0.75 if lvl == 1 else 0.9
    f = _CLOSE                                    # fake / found: the light has spiralled in -- there it is
    if kind == "fake":                            # oh! ...aw
        return (gx, gy, 0.85) if h < f else (gx, gy, 1.08) if h < f + 0.4 else (gx, gy + 2, 0.55)
    if kind == "found":
        return (gx, gy, 0.85) if h < f else (gx, gy - 1.5 * abs(math.sin((h - f) * 6)) * (h < f + 1.0), 1.08)
    return gx, gy, 0.85 if kind != "sweep" else 0.9


@lru_cache(maxsize=256)
def _sprite(seed, tries=0):
    """A random little figure, as (dx, dy) pixel offsets: a 5-7 tall half-grid of coin flips
    (denser down the middle), mirrored into a symmetric blob, lone pixels dropped. Too sparse or
    too solid -> roll again."""
    k = rand(*seed) * 9973 + tries * 31.7          # fold the seed: rand only reads its first 5 inputs
    h, half = 5 + int(rand(k, 1) * 3), 3 + int(rand(k, 2) * 2)
    p = 0.35 + 0.2 * rand(k, 3)
    half_rows = [[rand(k, 4, y, x) < p + 0.15 * (x == half - 1) for x in range(half)] for y in range(h)]
    grid = [row + row[-2::-1] for row in half_rows]           # mirror about the centre column
    if rand(k, 5) < 0.3:                                      # some lie on their side
        grid = [list(col) for col in zip(*grid)]
    gh, gw = len(grid), len(grid[0])
    on = lambda x, y: 0 <= y < gh and 0 <= x < gw and grid[y][x]
    pts = tuple((x - gw // 2, y - gh // 2) for y in range(gh) for x in range(gw)
                if grid[y][x] and (on(x - 1, y) or on(x + 1, y) or on(x, y - 1) or on(x, y + 1)))
    if 9 <= len(pts) <= 0.7 * gh * gw or tries > 8:
        return pts
    return _sprite(seed, tries + 1)


@lru_cache(maxsize=4)
def _litter(c):
    """[(x, y, seed)]: random things lying along the light's own path this search (so it keeps
    running into them), clear of the stops' things, of each other and of the eyes."""
    spots, out = [s[3] for s in _story(c)], []
    for k in range(200):
        if len(out) == _LITTER:
            break
        x, y = _light(c * _CYCLE + rand(c, 20, k) * _CYCLE)[:2]
        x, y = x + (rand(c, 21, k) - 0.5) * 6, y + (rand(c, 22, k) - 0.5) * 6
        if not (x < 21 or x > 107 or y < 8 or y > 56) or not (3 < x < 125 and 3 < y < 61):
            continue                              # only out in the free margins
        if (all(math.hypot(x - sx, y - sy) > 9 for sx, sy in spots)
                and all(math.hypot(x - a, y - b) > 8 for a, b, _ in out)):
            out.append((x, y, (c, 23, k)))
    return tuple(out)


def _icon(d, x, y, name, now=0.0):
    """A small silhouette, cut black out of the light."""
    x, y = round(x), round(y)
    if isinstance(name, tuple):                   # a generated thing
        d.point([(x + dx, y + dy) for dx, dy in _sprite(name)], fill=0)
    elif name == "cat":                           # the cat's face filling the light, cut black out of it
        tw = 1 if now % 2.7 < 0.12 else 0         # now and then an ear flicks
        d.ellipse([x - 6, y - 3, x + 6, y + 5], fill=0)                          # head
        d.polygon([(x - 6, y), (x - 5 - tw, y - 8 + tw), (x - 1, y - 3)], fill=0)   # ears
        d.polygon([(x + 6, y), (x + 5, y - 8), (x + 1, y - 3)], fill=0)
        d.line([(x - 4 - tw, y - 5 + tw), (x - 4, y - 3)], fill=1)               # the light through its ears
        d.line([(x + 4, y - 5), (x + 4, y - 3)], fill=1)
        if now % 3.2 > 0.15:                      # eyes shining back, a slow blink now and then
            d.rectangle([x - 4, y, x - 3, y + 1], fill=1)
            d.rectangle([x + 3, y, x + 4, y + 1], fill=1)
        else:
            d.line([(x - 4, y + 1), (x - 3, y + 1)], fill=1)
            d.line([(x + 3, y + 1), (x + 4, y + 1)], fill=1)
        d.point([(x, y + 2), (x - 2, y + 3), (x - 1, y + 4), (x + 1, y + 4), (x + 2, y + 3)], fill=1)   # nose, a little w
        for sgn in (-1, 1):                       # whiskers, reaching out across the light
            d.line([(x + sgn * 6, y + 2), (x + sgn * 9, y + 1)], fill=0)
            d.line([(x + sgn * 6, y + 3), (x + sgn * 9, y + 4)], fill=0)
    elif name == "coin":
        d.ellipse([x - 2, y - 2, x + 2, y + 2], outline=0)


def _thing(kind, u, tr, junk):
    """What's at this stop right now, or None."""
    if kind == "eyes":
        return "cat" if 1.1 < u < 1.7 else None
    return {"junk": junk, "fake": "coin", "found": "cat"}.get(kind)


def _scene(now):
    """The light as a bool mask: the pool with a dithered rim, whatever's there cut out of it."""
    c, i, (t0, t1, kind, (sx, sy), tr, junk), u = _stop(now)
    x, y, r, lvl = _light(now)
    m = np.zeros((_H, _W), bool)
    if lvl:
        dist = np.hypot(_XX - x, _YY - y)
        if lvl == 2:
            m = (dist < r - 0.5) | ((dist < r + 0.7) & (_DITHER < 0.5))   # crisp core, a soft 1px rim
        else:
            m = (dist < r) & (_DITHER < 0.3)      # weak batteries: a thin, grainy pool
        cut = Image.new("1", (_W, _H), 1)
        cd = ImageDraw.Draw(cut)
        for lx, ly, seed in _litter(c):           # whatever the light happens to pass over
            if math.hypot(lx - x, ly - y) < r + 5:
                _icon(cd, lx, ly, seed)
        thing = _thing(kind, u, tr, junk)
        if thing:
            _icon(cd, sx, sy, thing, now)
        m &= np.asarray(cut, dtype=bool)
    if kind == "eyes" and 0.15 < u < 1.1 and not 0.5 < u < 0.6:   # glowing eyes in the dark, blinking once
        m[sy - 1, sx - 2] = m[sy - 1, sx + 2] = True
    return m


def _marks(d, now):
    """'?' / '!' marks and the glints, drawn crisp on top of the light."""
    c, i, (t0, t1, kind, (sx, sy), tr, _), u = _stop(now)
    h = u - tr
    f = h - _CLOSE                                # s since the light closed in on the thing
    mark = None
    if kind == "hmm" and h > 0.3:
        mark, sx, sy, a = "?", *_light(now)[:2], h - 0.3
    elif kind == "eyes" and 0.25 < u < 0.75:
        mark, a = "!", u - 0.25
    elif kind == "eyes" and u > 1.75:
        mark, a = "?", u - 1.75
    elif kind == "fake" and 0 < f < 0.5:
        mark, a = "!", f
    elif kind == "found" and f > 0:
        mark, a = "!", f
    if kind in ("found", "fake") and f > 0 and (kind == "found" or f < 0.5):
        k = int(f * 6) % 2                        # a glint, twinkling just outside the light
        for g in range(4):
            ang = math.pi / 4 * (2 * g + k)
            r0, r1 = _R + 2, _R + 4 + k
            d.line([(sx + r0 * math.cos(ang), sy + r0 * math.sin(ang)),
                    (sx + r1 * math.cos(ang), sy + r1 * math.sin(ang))], fill=1)
    if mark is None:
        return
    rise = 3 * (1 - smoothstep(min(1.0, a / 0.2)))   # it pops up into place
    mx, my = round(sx) - 1, (sy + _R + 4 if sy < 32 else sy - _R - 14) + rise   # in the light's own column
    if mark == "!":
        d.rectangle([mx, my, mx + 1, my + 6], fill=1)
        d.rectangle([mx, my + 8, mx + 1, my + 9], fill=1)
    else:
        d.arc([mx - 2, my, mx + 4, my + 6], 200, 90, fill=1, width=2)
        d.line([(mx + 1, my + 6), (mx + 1, my + 7)], fill=1, width=2)
        d.rectangle([mx, my + 9, mx + 1, my + 10], fill=1)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    img = frame(d)
    if img is None:
        return
    marks = Image.new("1", (W, H))
    _marks(ImageDraw.Draw(marks), now)
    layer = _scene(now) | np.asarray(marks, dtype=bool)
    eyes = np.asarray(img, dtype=bool)
    halo = eyes.copy()                            # the eyes grown by 1px: the light slips behind them
    halo[1:] |= eyes[:-1]; halo[:-1] |= eyes[1:]
    halo[:, 1:] |= halo[:, :-1]; halo[:, :-1] |= halo[:, 1:]
    img.frombytes(np.packbits(eyes | (layer & ~halo), axis=1).tobytes())


def _mood():
    c, i, (t0, t1, kind, _, tr, _j), u = _stop(_clock[0])
    if kind == "found" and u > tr + _CLOSE:
        return "happy"
    if kind == "eyes" and 0.25 < u < 1.6:
        return "surprised"
    return "attentive"


class _Searching:
    """An Action whose face follows the story (the engine reads `mood` every frame)."""
    name = "searching"
    pose = staticmethod(_pose)
    overlay = staticmethod(_overlay)
    expired = None
    still = False
    tic = None
    mood = property(lambda self: _mood())


ACTION = _Searching()


if __name__ == "__main__":                        # ponytail check: every search fits its slot and ends on the find
    for c in range(300):
        st = _story(c)
        assert abs(st[-1][1] - _CYCLE) < 1e-6 and st[-1][2] == "found", (c, st[-1])
        assert all(a[3] != b[3] for a, b in zip(st, st[1:])), c
        assert all(a[2] != b[2] for a, b in zip(st, st[1:])), c
    print("ok")
