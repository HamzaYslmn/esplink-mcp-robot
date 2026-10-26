"""Gaze down at the Docker container-whale riding a live sea -- deploying. A round-bellied whale with
a 4-3-1 stack of containers on its flat back and a curled tail, half under the waves (the part below
the surface goes dim), heaving and rolling on a sea whose weather builds and calms.

Every few seconds something happens on board:
  spout     it blows from its blowhole
  breach    it leaps clear, hangs, and splashes back down
  slap      the tail rears up and slaps the water
  rollout   the top container lifts off and a fresh one drops in its place
  rolling   a rolling update: each container flashes in turn
  swell     a rogue wave rolls through and it rides up over it

Self-check: `cd src && uv run python -m faces.actions.deploying`."""
import math
from functools import cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from ..primitives import flip, frame, halftone, rand
from ..spec import Action

_SLOT = 6.0                    # s per event slot: one event somewhere in each
_EVENTS = (("spout", 1.3), ("breach", 1.6), ("slap", 1.2), ("rollout", 1.7), ("rolling", 1.5), ("swell", 3.0))
_BOX = (7, 4)                  # container px, with a 1 px gap between
_ROWS = ((0, 1, 2, 3), (1, 2, 3), (2,))   # the stack: columns filled per row, bottom up
_BLOWHOLE, _TAIL = (-22, -1), (15, -1)      # whale-local: the head, ahead of the stack / where the tail roots


def _spectrum():
    # seven swells at random lengths/speeds/phases, built once -- summed live they never repeat,
    # so the surface is always alive: crests wander, overtake and merge. (k, omega, phase, base-amp);
    # long waves run faster -- deep-water dispersion omega = sqrt(g*k).
    waves = []
    for i in range(7):
        k = 2 * math.pi / (15 + rand(i) * 90)                  # random 15..105px wavelength
        waves.append((k, math.sqrt(5.0 * k) * (0.9 + 0.2 * rand(i + 13)),
                      rand(i + 23) * 6.283, 0.25 + 0.8 * rand(i + 7)))
    return waves


_SPECTRUM = _spectrum()   # constant; only each wave's amplitude rides the wind, scaled per frame


# -- the events ----------------------------------------------------------------------------------------
@cache
def _pick(s, prev):
    """(event, start s into its slot) for a slot seeded s -- never the same as the slot before."""
    names = [n for n, _ in _EVENTS if n != prev]
    name = names[int(rand(s, 1) * len(names))]
    dur = dict(_EVENTS)[name]
    return name, 0.5 + rand(s, 2) * (_SLOT - dur - 0.8)


def _event(now):
    """(event, seconds into it, its length) -- u outside 0..length when nothing's on."""
    T, seed = getattr(now, "t", now), getattr(now, "seed", 0)
    slot = T // _SLOT
    prev = _pick(int(rand(seed, slot - 1) * 1e6), None)[0]
    name, start = _pick(int(rand(seed, slot) * 1e6), prev)
    return name, T % _SLOT - start, dict(_EVENTS)[name]


def _bump(u, dur):
    """0 -> 1 -> 0 over an event, eased at both ends."""
    return math.sin(math.pi * min(1.0, max(0.0, u / dur))) ** 2


# -- the sea and the whale ------------------------------------------------------------------------------
def _sea(now):
    """The live surface: x -> y, plus the wind 0..1 (calm..gale) that's setting how tall it runs."""
    sea_at = lambda t: max(0.0, min(1.0, 0.5 + 0.34 * math.sin(t * 0.06) + 0.16 * math.sin(t * 0.015 + 1.3)))
    amp, (name, u, dur) = 0.4 + sea_at(now), _event(now)

    def surf(x):
        y = 60 + sum(ba * amp * math.sin(k * x - w * now + ph) for k, w, ph, ba in _SPECTRUM)
        if name == "swell" and 0 <= u < dur:                # a rogue wave rolling in from the right
            y -= 5 * _bump(u, dur) * math.exp(-((x - (160 - 70 * u)) / 13) ** 2)
        return y
    return surf, sea_at


def _ride(now):
    """(cx, waterline y, pitch degrees, lift) -- afloat on the wave under it, drifting downwind."""
    surf, sea_at = _sea(now)
    name, u, dur = _event(now)
    # the hull drifts downwind: right as the sea builds, easing back left as it calms (with inertia,
    # so the berth trails the weather by a beat). then each wave's orbit nudges it fore-and-aft.
    berth = 64 + (sea_at(now - 3.0) - 0.5) * 34
    cx = berth + (surf(berth + 2) - surf(berth - 2)) * 2
    sy = surf(cx)
    pitch = math.degrees(math.atan((surf(cx + 6) - surf(cx - 6)) / 12)) * 0.45
    lift = 0.0
    if name == "breach" and 0 <= u < 1.0:                   # a leap: up, hang, and nose back down
        lift = 13 * 4 * u * (1 - u)
        pitch -= 14 * math.sin(math.pi * u) * (1 - 2 * u)
    elif name == "breach" and 1.0 <= u < dur:               # ...and the bob after the splash
        lift = -2.5 * math.sin(math.pi * (u - 1.0) / (dur - 1.0))
    elif name == "rollout" and 1.25 <= u < dur:             # the fresh container lands: a dip
        lift = -1.5 * math.sin(math.pi * (u - 1.25) / (dur - 1.25))
    return cx, sy, pitch, lift


def _boxes(now):
    """[(x, y, lit)] whale-local containers (top-left corners off the deck at y=0); lit = flashing."""
    name, u, dur = _event(now)
    w, h = _BOX
    out = []
    for r, cols in enumerate(_ROWS):
        for c in cols:
            x, y = -19 + c * (w + 1), -(r + 1) * (h + 1) - 1    # a dark seam off the deck
            n = len(out)
            if name == "rollout" and r == len(_ROWS) - 1:   # off it goes, and a fresh one drops in
                if 0.45 <= u < 0.75:
                    continue
                if 0 <= u < 0.45:
                    y -= 40 * (u / 0.45) ** 2
                elif 0.75 <= u < 1.25:
                    y -= 40 * (1 - ((u - 0.75) / 0.5) ** 2)
            lit = name == "rolling" and 0 <= u - n * 0.12 < 0.3
            out.append((x, y, lit))
    return out


def _paint(g, now):
    """The whale and its stack, whale-local round (64, 32), on a layer g."""
    name, u, dur = _event(now)
    P = lambda x, y: (64 + x, 32 + y)
    g.chord([*P(-23, -12), *P(19, 13)], 0, 180, fill=1)     # the belly: a 'D' laid on its back
    g.rectangle([*P(-23, -1), *P(19, 0)], fill=1)           # ...with a flat deck
    slap = 0.0
    if name == "slap" and 0 <= u < 0.8:                     # the tail rears back, then cracks down
        slap = 28 * math.sin(math.pi * u / 0.6) if u < 0.6 else -40 * math.sin(math.pi * (u - 0.6) / 0.2)
    a = math.radians(slap)
    T = lambda x, y: P(_TAIL[0] + (x - _TAIL[0]) * math.cos(a) + (y - _TAIL[1]) * math.sin(a),
                       _TAIL[1] - (x - _TAIL[0]) * math.sin(a) + (y - _TAIL[1]) * math.cos(a))
    g.polygon([T(12, 3), T(14, -3), T(21, -9), T(23, -8), T(19, 1)], fill=1)          # the tail stock, curling up
    g.polygon([T(21, -8), T(17, -13), T(18, -15), T(22, -11), T(23, -9)], fill=1)    # left fluke
    g.polygon([T(21, -8), T(27, -11), T(28, -9), T(24, -7)], fill=1)                 # right fluke
    g.ellipse([*P(-16, 1), *P(-13, 4)], fill=0)            # an eye...
    g.point(P(-15, 2), fill=1)                              # ...with a glint
    w, h = _BOX
    for x, y, lit in _boxes(now):
        g.rectangle([*P(x, y), *P(x + w - 1, y + h - 1)], fill=0 if lit else 1, outline=1)
        for rib in () if lit else (1, 3, 5):                # corrugated sides (a flashing one goes hollow)
            g.line([P(x + rib, y + 1), P(x + rib, y + h - 2)], fill=0)


@cache
def _dim(W, H):
    return halftone(Image.new("L", (W, H), 110))           # under water: every other dot or so


def _overlay(d, W, H, now, ox=0.0, oy=0.0):  # the Docker whale riding a live sea -- "deploying"
    surf, _ = _sea(now)
    cx, sy, pitch, lift = _ride(now)
    lay = Image.new("1", (W, H), 0)
    _paint(ImageDraw.Draw(lay), now)
    deck = sy - 9 - lift                                    # the deck rides 9 px over the waterline
    lay = lay.rotate(pitch, resample=Image.NEAREST, translate=(cx - 64, deck - 32), center=(64, 32))

    line = [(x, surf(x)) for x in range(0, W + 1, 2)]
    water = Image.new("1", (W, H), 0)
    ImageDraw.Draw(water).polygon(line + [(W, H), (0, H)], fill=1)
    base = frame(d)
    base.paste(0, (0, 0), lay.convert("L").filter(ImageFilter.MaxFilter(3)).convert("1"))   # 1px black outline
    above = ImageChops.logical_and(lay, ImageChops.invert(water))
    base.paste(1, (0, 0), ImageChops.logical_or(above, ImageChops.logical_and(lay, _dim(W, H))))  # dim under water
    surface = Image.new("1", (W, H), 0)
    ImageDraw.Draw(surface).line(line, fill=1, width=1, joint="curve")
    base.paste(1, (0, 0), ImageChops.logical_and(surface, ImageChops.invert(lay)))   # the sea surface...
    base.paste(0, (0, 0), ImageChops.logical_and(surface, lay))   # ...a dark wave line across the whale
    _splash(d, now, cx, deck, pitch, surf)


def _splash(d, now, cx, deck, pitch, surf):
    """Spray: from the blowhole, round a breach's re-entry, off a tail slap."""
    name, u, dur = _event(now)
    a = math.radians(pitch)
    at = lambda x, y: (cx + x * math.cos(a) + y * math.sin(a), deck - x * math.sin(a) + y * math.cos(a))
    if name == "spout":
        bursts = [(at(*_BLOWHOLE), u, 1.0, 58, 24)]         # a tall plume, droplets raining back
    elif name == "breach":
        bursts = [((cx, surf(cx)), u - 0.92, 0.6, 26, 70)]  # a wide crown of spray as it comes down
    elif name == "slap":
        bursts = [(at(23, -2), u - 0.62, 0.6, 22, 80)]
    else:
        return
    for (x0, y0), v, life, speed, spread in bursts:
        for i in range(30):
            age = v - 0.25 * rand(i, 1)
            if not 0 <= age < life:
                continue
            ang = math.radians(-90 + (rand(i, 2) - 0.5) * spread)
            sp = speed * (0.6 + 0.4 * rand(i, 3))
            x, y = x0 + math.cos(ang) * sp * age, y0 + math.sin(ang) * sp * age + 60 * age * age
            if y < surf(x):
                flip(d, round(x), round(y))


def _pose(now):   # gaze down at the container-whale bobbing on the swell; look up with it on a leap
    name, u, dur = _event(now)
    gx, gy, h = math.sin(now * 0.25) * 4, 7 + math.sin(now * 1.7) * 1.2, 1.0
    if name == "breach":
        gy -= 4 * _bump(u, 1.0)
    elif name in ("spout", "rollout"):
        gy -= 2 * _bump(u, dur)
    elif name == "slap" and 0.6 <= u < 0.9:                 # a little flinch at the crack
        h -= 0.08 * math.sin(math.pi * (u - 0.6) / 0.3)
    return gx, gy, h


ACTION = Action("deploying", mood="neutral", pose=_pose, overlay=_overlay)


if __name__ == "__main__":
    seen, prev = set(), None
    for slot in range(400):
        name, start = _pick(int(rand(7, slot) * 1e6), prev)
        assert name != prev and 0.5 <= start and start + dict(_EVENTS)[name] <= _SLOT - 0.3, "fits its slot, no repeats"
        seen.add(name)
        prev = name
    assert seen == {n for n, _ in _EVENTS}, f"every event comes up: {seen}"
    assert len(_boxes(0.0)) == sum(map(len, _ROWS)) == 8, "a 4-3-1 stack"
    print("deploying ok")
