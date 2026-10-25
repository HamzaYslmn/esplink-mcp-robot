"""Naruto eyes -- Pip's own eyes take on every dojutsu in turn, starting from a random one each play:
Sharingan (awakens 1 -> 2 -> 3 tomoe, then blooms a Mangekyo), Rinnegan (six rippling rings; Rinne
Sharingan or Sasuke's variant), Byakugan (pupil-less, veins bulging at the temples), Tenseigan
(a pale flower round a dark pupil), Kurama (the Nine-Tails' slit) and Sage Mode (the toad bar).
Each grows out of the pupil and folds back into it to hand over.

Native by design: the engine draws the eyes as always -- shape, eased glances, breath, blinks --
and each pattern is carved into the lit eye pixels, so it rides every move and squashes with
every blink. Designs follow Narutopedia's galleries (naruto.fandom.com); white is the iris
colour, ink the black pattern.

Self-check: `cd src && uv run python -m faces.vibes.naruto_eyes`."""
import math

from PIL import Image, ImageChops, ImageDraw

from ..primitives import flip, frame, rand, smoothstep
from ..spec import Vibe

_TAU = 2 * math.pi
_SS = 4                        # supersample factor -> smooth curves on the 1-bit panel
_HAND = 0.5                    # s a pattern takes to grow out of / fold into the pupil between eyes


# -- drawing kit --------------------------------------------------------------------------------
class _Pen:
    """Draws in iris units (19 = rim) around the pupil (x right, y down) onto a supersampled tile.
    Ink is 0 on the white iris; fill=255 cuts white back in. `scaled(k)` shrinks toward the pupil.
    sx == sy keeps circles round; sy < sx flattens the pattern through a blink."""

    def __init__(self, d, cx, cy, sx, sy):
        self.d, self.cx, self.cy, self.sx, self.sy = d, cx, cy, sx, sy

    def scaled(self, k):
        return _Pen(self.d, self.cx, self.cy, self.sx * k, self.sy * k)

    def _xy(self, pts):
        return [(self.cx + x * self.sx, self.cy + y * self.sy) for x, y in pts]

    def disc(self, r, x=0.0, y=0.0, fill=0):
        (cx, cy), = self._xy([(x, y)])
        self.d.ellipse([cx - r * self.sx, cy - r * self.sy, cx + r * self.sx, cy + r * self.sy], fill=fill)

    def ring(self, r, width=1.0):
        self.d.ellipse([self.cx - r * self.sx, self.cy - r * self.sy, self.cx + r * self.sx, self.cy + r * self.sy],
                       outline=0, width=max(1, round(width * _SS)))

    def poly(self, pts, fill=0):
        self.d.polygon(self._xy(pts), fill=fill)

    def line(self, pts, width=1.0):
        self.d.line(self._xy(pts), fill=0, width=max(1, round(width * _SS)), joint="curve")


def _polar(r, a):
    return r * math.cos(a), r * math.sin(a)


def _tomoe(pen, a, ring, size=3.6, tail=9):
    """A comma: a round head on the ring with a tail tapering behind the spin (longer = motion blur)."""
    for k in range(tail):
        pen.disc(size * (1 - k / tail) ** 0.7, *_polar(ring + k * size / 8, a - k * 0.15))


def _carve(d, x, y, w, h, eye, paint):
    """Carve paint(pen, eye) into one eye exactly where the engine just drew it (x, y, w, h): the
    pattern is drawn round at the eye's width on a supersampled tile -- a glance's parallax narrows
    the eye, it doesn't stretch the pattern -- flattened only as the eye blinks shut, and kept only
    where the eye is lit."""
    img = frame(d)
    x0, y0, w, h = round(x), round(y), round(w), round(h)          # the same rounding rounded_rect uses
    if img is None or w < 4 or h < 3:
        return                                                      # mid-blink sliver: leave it plain
    tile = Image.new("L", (w * _SS, h * _SS), 255)
    paint(_Pen(ImageDraw.Draw(tile), w * _SS / 2, h * _SS / 2, w * _SS / 38, min(w, h * 1.05) * _SS / 38), eye)
    pattern = tile.resize((w, h), Image.BOX).point(lambda v: 255 if v >= 200 else 0)   # >~1/4 inked stays ink
    box = (x0, y0, x0 + w, y0 + h)
    img.paste(ImageChops.multiply(img.crop(box).convert("L"), pattern).convert("1"), box[:2])


# -- Mangekyo patterns (Narutopedia: Mangekyō Sharingan "Designs") --------------------------------
def _band(c, w, r0, r1, n=12):
    """A tapering band: centre-line angle c(f), half-width w(f) (rad), radius r0 -> r1."""
    pts = [(r0 + (r1 - r0) * f, c(f), w(f)) for f in (j / n for j in range(n + 1))]
    return [_polar(r, a + h) for r, a, h in pts] + [_polar(r, a - h) for r, a, h in pts[::-1]]


def _vesica(axis, length=18.5, width=9.5, n=12):
    """A pointed ellipse through the pupil along `axis` (tips at +-length)."""
    ca, sa = math.cos(axis), math.sin(axis)
    pts = []
    for sign in (1, -1):
        for j in range(n + 1):
            t = -1 + 2 * j / n
            x, y = length * t, sign * width * (1 - t * t)
            pts.append((x * ca - y * sa, x * sa + y * ca))
    return pts


def _itachi(pen, a):
    """Three broad scythe blades curving from a black hub out to the rim; a red dot in the hub."""
    for i in range(3):
        a0 = a + i * _TAU / 3
        pen.poly(_band(lambda f: a0 + 1.5 * f ** 1.4, lambda f: 0.55 * (1 - f) + 0.04, 4, 19))
    pen.disc(6)
    pen.disc(2.5, fill=255)


def _shisui(pen, a):
    """A four-point shuriken with concave edges, tips swept at the rim; a bullseye centre."""
    pts = []
    for i in range(4):
        t = a + i * _TAU / 4
        pts += [_polar(19, t + 0.12), _polar(12, t + 0.5), _polar(9.5, t + _TAU / 8 + 0.15), _polar(11.5, t + _TAU / 4 - 0.3)]
    pen.poly(pts)
    pen.disc(4.6, fill=255)
    pen.disc(2.2)


def _kakashi(pen, a):
    """Kakashi / Obito: three tapered spokes hub-to-rim, each throwing a thin crescent scythe."""
    for i in range(3):
        a0 = a - math.pi / 2 + i * _TAU / 3
        pen.poly([_polar(6, a0 - 0.5), _polar(19, a0), _polar(6, a0 + 0.5)])
        pen.poly(_band(lambda f: a0 + 0.15 + 1.75 * f, lambda f: 0.17 * (1 - f) + 0.03, 16, 12.5))
    pen.disc(7.5)
    pen.disc(4.2, fill=255)


def _sasuke_star(pen, a):
    """Sasuke's inverted scheme: three crossed red vesica petals (a six-point star) on a black iris."""
    pen.disc(27)                                            # the whole eye goes black, corners too
    for i in range(3):                                      # (the wiki's thin petal outlines blur at 34px)
        pen.poly(_vesica(a + i * math.pi / 3), fill=255)


def _sasuke(pen, a):
    _sasuke_star(pen, a)
    pen.disc(3.5)


def _madara(pen, a):
    """Madara: a black band looping around the pupil through three ringed circles."""
    for i in range(3):
        a0 = a + i * _TAU / 3
        pen.line([_polar(11 + 3.5 * math.sin(math.pi * f), a0 + _TAU / 3 * f) for f in (j / 14 for j in range(15))], 2.4)
    for i in range(3):
        x, y = _polar(11, a + i * _TAU / 3)
        pen.disc(4.3, x, y)
        pen.disc(2.4, x, y, fill=255)
    pen.disc(3.5)


def _spokes(pen, a, r0, width=2.4):
    """Three straight, thick spokes out to the rim (Izuna, Madara's Eternal)."""
    for i in range(3):
        t = a - math.pi / 2 + i * _TAU / 3
        ca, sa, cp, sp = math.cos(t), math.sin(t), -math.sin(t), math.cos(t)
        pen.poly([(r0 * ca + width * cp, r0 * sa + width * sp), (19 * ca + width * cp, 19 * sa + width * sp),
                  (19 * ca - width * cp, 19 * sa - width * sp), (r0 * ca - width * cp, r0 * sa - width * sp)])


def _izuna(pen, a):
    """Izuna: a big black disc with a red centre dot, three straight spokes to the rim."""
    _spokes(pen, a, 10)
    pen.disc(12.5)
    pen.disc(2.3, fill=255)


def _eternal_sasuke(pen, a):
    """Sasuke's Eternal: his star overlaid with a straight-bladed black pinwheel, a red centre."""
    _sasuke_star(pen, a)
    for i in range(3):
        t = a + math.pi / 2 + i * _TAU / 3
        pen.poly([_polar(3, t - 1.0), _polar(10, t - 0.22), _polar(17, t), _polar(10, t + 0.35), _polar(3, t + 1.0)])
    pen.disc(3.6, fill=255)


def _eternal_madara(pen, a):
    """Madara's Eternal: his ringed loop tied to the rim by Izuna's three straight spokes."""
    _spokes(pen, a + math.pi / 3, 13.5, 2.2)
    _madara(pen, a)


def _indra(pen, a):
    """Indra: one thick black spiral of ~3 turns, curling tight at the centre."""
    pen.line([_polar(18 * (1 - f) + 1.5, a + 3 * _TAU * f) for f in (j / 90 for j in range(91))], 2.2)


def _sarada(pen, a):
    """Sarada: eight black spikes standing on a red central disc, a black pupil."""
    for i in range(8):
        t = a + i * _TAU / 8
        pen.poly([_polar(8.5, t - 0.36), _polar(18.5, t), _polar(8.5, t + 0.36)])
    pen.disc(3.6)


_MANGEKYO = (_itachi, _shisui, _kakashi, _sasuke, _madara, _izuna, _eternal_sasuke, _eternal_madara,
             _indra, _sarada)


# -- the eyes, each a scene(t, T, seed) on its own clock -> (paint(pen, eye), props(d, centres)) ----
def _sharingan_spin(t):
    """Continuous spin: a slow drift plus a smooth 5-turn burst through the Mangekyo window."""
    return 0.6 * t + 5 * _TAU * smoothstep((t - 5.5) / 2.9)


def _sharingan_pull(t):
    """0..1 how far the tomoe are sucked into the pupil around the Mangekyo (6.3 .. 7.9 s)."""
    return smoothstep((t - 5.8) / 0.5) * smoothstep((8.4 - t) / 0.5)


def _sharingan(t, T, seed):
    """Awakens 1 -> 2 -> 3 tomoe, whips them into a blur, blooms a Mangekyo with a shockwave."""
    a = _sharingan_spin(t)
    tail = min(26, 9 + int((_sharingan_spin(t + 0.02) - a) / 0.02 * 0.5))   # faster spin -> longer tails
    n = 1 + smoothstep((t - 1.5) / 0.6) + smoothstep((t - 3.0) / 0.6)
    m, f = int(n), n - int(n)                                       # whole tomoe + the one growing in
    pull = _sharingan_pull(t)
    bloom = smoothstep((t - 6.3) / 0.3) * smoothstep((7.9 - t) / 0.3)
    ring = 11 * (1 - 0.75 * pull)
    pattern = _MANGEKYO[int(rand(seed, 1) * len(_MANGEKYO))]
    hand = _hand(t, T)

    def paint(pen, eye):
        pen = pen.scaled(hand)
        if pull < 1:
            if ring > 5:
                pen.ring(ring, 0.9)
            for i in range(m + (f > 0.02)):
                grow = f if i == m else 1.0                         # the newcomer spirals out of the pupil
                _tomoe(pen, a + i * _TAU / (m + f), 4 + (ring - 4) * grow, 3.6 * grow * (1 - 0.4 * pull), tail)
            pen.disc(4)
        if bloom > 0.02:
            pattern(pen.scaled(bloom), a)

    def props(d, centres):
        if 0 < t - 6.3 < 0.25:                                      # shockwave as it awakens
            r = 21 + 40 * (t - 6.3)
            for cx, cy in centres:
                d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=1)

    return paint, props


_RINGS = tuple(2.9 * i for i in range(1, 7))                       # the Rinnegan's six rings
_RINNE = (6.0, 11.0, 16.0)                                          # the Rinne Sharingan's three
_UP = -math.pi / 2                                                  # tomoe "top, lower-left, lower-right"


def _rinnegan(t, T, seed):
    """Six breathing rings and a rolling ripple; mid-scene the Rinne Sharingan (nine tomoe on three
    rings) or Sasuke's (six tomoe on the inner rings of his left eye, his Eternal Mangekyo in the right)."""
    f = smoothstep((t - 4.0) / 0.7) * smoothstep((8.5 - t) / 0.7)
    sasuke = rand(seed, 2) < 0.5
    a, breath, ripple = t * 0.25, 0.3 * math.sin(t * 1.5), 2 + 17 * (t % 3.0) / 3.0
    hand = _hand(t, T)

    def rings(pen, radii, k=1.0):
        for r in radii:
            if r * k > 2:
                pen.ring((r + breath) * k, 0.8)

    def paint(pen, eye):
        pen = pen.scaled(hand)
        if sasuke and eye == 0:                                     # his right eye (screen left)
            rings(pen, _RINGS, 1 - f)
            if f > 0.02:
                _eternal_sasuke(pen.scaled(f), a)
            pen.disc(1.8 * (1 - f))
            return
        if not sasuke and f:                                        # six rings melt to the Rinne's three
            rings(pen, _RINGS if f < 0.5 else _RINNE)
            for j, ring in enumerate(_RINNE):
                for i in range(3):
                    _tomoe(pen, a + _UP + j * math.pi / 3 + i * _TAU / 3, ring, 2.3 * f, 7)
            pen.disc(2.5)
            return
        rings(pen, _RINGS)
        if ripple < 18.5:
            pen.ring(ripple, 0.5)
        if sasuke and f:                                            # his left eye: six tomoe, inner two rings
            for j, ring in enumerate(_RINGS[1:3]):
                for i in range(3):
                    _tomoe(pen, a + _UP + j * math.pi / 3 + i * _TAU / 3, ring, 1.9 * f, 6)
        pen.disc(1.8)

    return paint, None


_VEINS = (150, 172, 194, 216, 238)                                  # temple-side rim angles (left eye)


def _vein(d, cx, cy, deg, seed, g, thick):
    """A bulging vein: a wiggly trunk walking out from beside the eye, with one side branch."""
    a = math.radians(deg)
    x, y = cx + 20 * math.cos(a), cy + 20 * math.sin(a)
    for k in range(int((5 + 4 * rand(seed, 1)) * g)):
        a += (rand(seed, k, 2) - 0.5) * 0.9
        nx, ny = x + 2.6 * math.cos(a), y + 2.6 * math.sin(a)
        d.line([x, y, nx, ny], fill=1, width=2 if thick and k < 3 else 1)
        if k == 2:                                                  # a branch peels off
            b = a + (0.7 if rand(seed, 3) > 0.5 else -0.7)
            d.line([nx, ny, nx + 5 * g * math.cos(b), ny + 5 * g * math.sin(b)], fill=1)
        x, y = nx, ny


def _byakugan(t, T, seed):
    """Pupil-less, just a faint broken pupil outline that sharpens; veins surge beside the temples,
    throbbing, and a ring of 360-degree sight sweeps out."""
    g = _hand(t, T, 0.8)

    def paint(pen, eye):
        if g > 0.4:
            for lo, hi in ((1.75, 4.36), (4.89, 7.5)):
                pen.line([_polar(6, lo + (hi - lo) * j / 10) for j in range(11)], 0.9)

    def props(d, centres):
        thick = (t % 1.1) < 0.18                                    # the heartbeat throb
        sweep = (t - 1.0) / 1.6
        for eye, (cx, cy) in enumerate(centres):
            if g > 0.05:
                for i, deg in enumerate(_VEINS):
                    _vein(d, cx, cy, deg if eye == 0 else 180 - deg, eye * 10 + i, g, thick)
            if 0 < sweep < 1:                                       # 360-degree sight sweeping out
                r = 21 + 55 * smoothstep(sweep)
                for k in range(0, 360, 10):
                    flip(d, cx + r * math.cos(math.radians(k)), cy + r * math.sin(math.radians(k)))

    return paint, props


def _tenseigan(t, T, seed):
    """A solid dark pupil with a pale flower radiating from it, turning, swelling with a glow."""
    u = (t % 3.0) / 3.0
    glow = smoothstep(u / 0.25) * (1 - smoothstep((u - 0.25) / 0.75))
    a, reach, hand = t * 0.3, 13.5 + 2 * glow, _hand(t, T)

    def paint(pen, eye):
        pen = pen.scaled(hand)
        for i in range(8):                                          # petal outlines: the pale flower
            p = a + i * _TAU / 8
            pen.line([_polar(5.5, p - 0.32), _polar(reach * 0.6, p - 0.24), _polar(reach, p),
                      _polar(reach * 0.6, p + 0.24), _polar(5.5, p + 0.32)], 0.7)
        pen.disc(5.5)

    def props(d, centres):
        if glow > 0.3 and hand > 0.9:                               # rays flare off the eyes
            for cx, cy in centres:
                for i in range(8):
                    p = -a + i * _TAU / 8
                    d.line([cx + 21 * math.cos(p), cy + 21 * math.sin(p),
                            cx + (21 + 5 * glow) * math.cos(p), cy + (21 + 5 * glow) * math.sin(p)], fill=1)

    return paint, props


def _kurama(t, T, seed):
    """The Nine-Tails' vertical slit: breathes wide and thin, drifts, snaps to a razor in rage."""
    u = t % 3.5
    rage = smoothstep(u / 0.08) * (1 - smoothstep((u - 1.2) / 0.5)) if u < 1.7 else 0.0
    w = (2.2 + 1.6 * math.sin(t * 0.8)) * (1 - 0.7 * rage) * _hand(t, T)
    gx = 3 * math.sin(t * 0.37)

    def paint(pen, eye):
        side = [(gx + w * math.sin(s), -15 * math.cos(s)) for s in (math.pi * j / 12 for j in range(13))]
        pen.poly(side + [(2 * gx - x, y) for x, y in side[::-1]])

    return paint, None


def _sage(t, T, seed):
    """Sage Mode: the toad's horizontal bar pupil, breathing a touch."""
    h = 2.6 * (1 + 0.08 * math.sin(t * 1.3))
    return lambda pen, eye: pen.scaled(_hand(t, T)).poly([(-9, -h), (9, -h), (10.5, 0), (9, h), (-9, h), (-10.5, 0)]), None


_SCENES = ((_sharingan, 10.0), (_rinnegan, 12.0), (_byakugan, 8.0), (_tenseigan, 7.0),
           (_kurama, 7.0), (_sage, 9.0))
_TOTAL = sum(T for _, T in _SCENES)


def _hand(t, T, ramp=_HAND):
    """0..1: a scene's pattern grows out of the pupil at its start and folds back in at its end."""
    return smoothstep(t / ramp) * smoothstep((T - t) / ramp)


def _scene(now):
    """(scene fn, seconds into it, its length, seed) -- a random first eye per play, then in order."""
    seed = getattr(now, "seed", 0)
    t = getattr(now, "t", now)
    cycle, t = divmod(t, _TOTAL)
    i = int(rand(seed) * len(_SCENES))
    for _ in _SCENES:
        fn, T = _SCENES[i]
        if t < T:
            return fn, t, T, rand(seed, cycle, i)
        t -= T
        i = (i + 1) % len(_SCENES)
    return _SCENES[i][0], 0.0, _SCENES[i][1], seed


def _gaze(now):
    """Where the eyes look: a quick dart to a new spot every ~2.6s, often back to centre -- the
    resting face's idle glances, which the engine doesn't run while a vibe holds the face."""
    k, u = divmod(now, 2.6)

    def spot(i):
        if rand(i, 3) < 0.35:
            return 0.0, 0.0
        return (rand(i, 1) - 0.5) * 28, (rand(i, 2) - 0.5) * 12

    (x0, y0), (x1, y1), e = spot(k - 1), spot(k), smoothstep(u / 0.18)
    return x0 + (x1 - x0) * e, y0 + (y1 - y0) * e


def _pose(now):   # glance around like the resting eyes; the Sharingan locks dead-centre as it blooms
    fn, t, _, _ = _scene(now)
    x, y = _gaze(now)
    k = 1 - _sharingan_pull(t) if fn is _sharingan else 1.0
    return x * k, y * k, 1.0


_centres = {}                  # eye -> centre where the engine drew it this frame (for the props)


def _eyes(d, x, y, w, h, right, now):
    """Engine hook: restyle each eye as it's drawn, at its exact live rect."""
    fn, t, T, seed = _scene(now)
    _centres[int(right)] = (x + w / 2, y + h / 2)
    _carve(d, x, y, w, h, int(right), fn(t, T, seed)[0])


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    fn, t, T, seed = _scene(now)
    props = fn(t, T, seed)[1]
    if props:
        props(d, [_centres[e] for e in sorted(_centres)])


VIBE = Vibe("naruto_eyes", mood="neutral", pose=_pose, overlay=_overlay, eyes=_eyes)


if __name__ == "__main__":
    from ..spec import Now
    seen = {_scene(Now(0.0, t, 7))[0] for t in range(0, int(_TOTAL), 2)}
    assert seen == {fn for fn, _ in _SCENES}, "every eye should play within one cycle"
    assert len({_scene(Now(0.0, 0.0, s))[0] for s in range(40)}) > 3, "a random first eye per play"
    assert _hand(0.0, 9) == 0 and _hand(4.5, 9) == 1 and _hand(9.0, 9) == 0, "patterns grow in and fold away"
    assert len({int(rand(s, 1) * len(_MANGEKYO)) for s in range(200)}) == len(_MANGEKYO), "every Mangekyo comes up"
    print("naruto_eyes ok")
