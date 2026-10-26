"""Testing -- Pip eyeing a test tube in the corner. Between experiments it simmers on its own rhythms
(the odd bubble, a bout of the jitters, a thin wisp of gas), and every few seconds something happens:
  dose     a dropper reaches in and lets a drop fall -- the liquid flickers and changes, fizzing hard
  shake    the tube's given a good shake: it rattles, the liquid sloshes side to side, bubbles burst
  pop      pressure builds, the bubbles race -- and the stopper shoots out, tumbles, and drops back in
  foam     it froths up over the rim and dribbles down the glass, a wisp of smoke on top
  glow     the mix comes good: it glows, light spilling round the tube, a sparkle -- Pip lights up
  boom     it blows: a flash, a pop of smoke, the glass gone sooty and empty -- Pip jolts -- and then
           it's refilled and stoppered for the next go
  rings    it puffs out smoke rings that drift off toward Pip
  crystals spikes of crystal grow up through the liquid, and glint
  freeze   frost creeps up the glass, the liquid turns to ice, Pip shivers -- then it thaws and drips
  critter  a little goo blob pushes the stopper up, peeks out, blinks at Pip, and ducks back down
  bubble   a big bubble swells at the mouth, floats over, and pops right by Pip's eye -- a blink
  lens     a magnifying glass slides up for a closer look: big lazy bubbles, a germ wriggling
The glass has graduations up its side.
Pip's eyes live with it: plain and open most of the time, narrowing into a focused squint in spells
of close study or as a reaction builds, popping wide at a pop or a blast, brightening at a glow --
always easing between, never snapping.

Self-check: `cd src && uv run python -m faces.actions.testing`."""
import math
from functools import cache

from PIL import Image

from ..painters import lids
from ..primitives import flip, frame, halftone, rand, smoothstep, soft_spot
from ..spec import Action

_STRETCH = 14.0                # s per string of experiments
_X, _TOP, _BOT, _HW = 118, 34, 60, 5   # the tube: centre x, mouth y, bottom y, half-width
_LIQ = _TOP + 11               # the liquid's surface
_KINDS = (("dose", 0.12, 2.2), ("shake", 0.1, 1.4), ("pop", 0.1, 1.9), ("foam", 0.09, 2.0),
          ("glow", 0.08, 1.6), ("boom", 0.06, 2.8), ("rings", 0.09, 2.3), ("crystals", 0.08, 2.4),
          ("freeze", 0.08, 2.6), ("critter", 0.07, 2.4), ("bubble", 0.07, 2.4), ("lens", 0.06, 2.6))
#                              (event, weight, seconds)
_LIDDED = ("dose", "rings", "bubble")                   # the stopper's set aside for these


# -- the plan ------------------------------------------------------------------------------------------
@cache
def _plan(s):
    """((start s, kind, seconds), ...) -- a few experiments with simmering lulls between."""
    out, t, last, i = [], 0.8 + rand(s, 0) * 0.8, None, 0
    while True:
        i += 1
        opts = [(k, w, d) for k, w, d in _KINDS if k != last]
        r, pick = rand(s, i, 1) * sum(w for _, w, _ in opts), opts[0]
        for o in opts:
            if r < o[1]:
                pick = o
                break
            r -= o[1]
        if t + pick[2] > _STRETCH - 0.4:
            break
        out.append((t, pick[0], pick[2]))
        t, last = t + pick[2] + 0.7 + rand(s, i, 2) * 1.0, pick[0]
    return tuple(out)


def _event(now):
    """(kind, seconds into it, its length) of the experiment under way, or (None, 0, 0) in a lull."""
    T, seed = getattr(now, "t", now), getattr(now, "seed", 0)
    t = T % _STRETCH
    for t0, kind, dur in _plan(int(rand(seed, T // _STRETCH) * 1e6)):
        if t0 <= t < t0 + dur:
            return kind, t - t0, dur
    return None, 0.0, 0.0


def _bump(u, a, b):
    """0 -> 1 -> 0 between a and b seconds."""
    return math.sin(math.pi * (u - a) / (b - a)) if a <= u < b else 0.0


# -- the tube ------------------------------------------------------------------------------------------
def _simmer(now):
    """The baseline rhythms when nothing's happening: (jitters, bubbling, gas), each 0..1."""
    env = lambda n, thr, soft: max(0.0, min(1.0, (n - thr) / soft))
    return (env(math.sin(now * 0.8) + math.sin(now * 1.9 + 1.0), 0.85, 0.3),
            env(math.sin(now * 0.5 + 0.7) + math.sin(now * 1.27 + 2.4), -0.2, 0.55),
            env(math.sin(now * 0.41) + math.sin(now * 0.93 + 1.6), 0.65, 0.5))


def _cap_at(kind, u, dur, cx):
    """(x, y) of the stopper's top -- shot out on a pop (an arc up and back down into the mouth), lifted
    aside for a dose, gone in a blast until it drops back in."""
    if kind == "pop" and 0.7 <= u < 1.7:
        f = (u - 0.7) / 1.0
        return cx - 26 * math.sin(math.pi * f) * 0.6, _TOP - 4 - 30 * math.sin(math.pi * f)
    if kind in _LIDDED and u < dur:
        return cx + 9 * _bump(u, 0.0, dur), _TOP - 4 - 5 * _bump(u, 0.0, dur)
    if kind == "critter":                                   # pushed up from below by whatever's in there
        k = smoothstep(min((u - 0.2) / 0.3, 1.0, (dur - 0.3 - u) / 0.3))
        return cx + 1 * k, _TOP - 4 - 12 * k               # riding on its head
    if kind == "boom":
        if u < 2.2:
            return None
        return cx, _TOP - 4 - 20 * (1 - smoothstep((u - 2.2) / 0.5))
    return cx, _TOP - 4


def _liquid(d, cx, level, tilt, look, mix=0.0, phase=0):
    """The liquid: a column up to `level`, its surface tilted by a slosh. Solid, with `mix` (0..1) of its
    pixels -- a fixed scatter, so it dissolves in and out rather than snapping -- turned to `look`:
    'shimmer' (a crawling checker), 'dark' or 'ice'."""
    bot, hw = _BOT, _HW
    for y in range(round(level - abs(tilt)) - 1, bot + 1):
        for x in range(cx - hw + 1, cx + hw):
            if y < level + tilt * (x - cx) / hw:
                continue
            if y > bot - hw and (x - cx) ** 2 + (y - (bot - hw)) ** 2 > (hw - 1) ** 2:
                continue                                    # the rounded foot
            on = True
            if mix and rand(x, y, 9) < mix:
                on = {"shimmer": (x + y + phase) % 2 == 0, "dark": (x + 2 * y + phase) % 5 == 0,
                      "ice": (x + y) % 7 != 0}[look]
            if on:
                d.point((x, y), fill=1)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    img = frame(d)
    if img is None:
        return
    kind, u, dur = _event(now)
    shake, bubl, gasl = _simmer(now)
    env = smoothstep(min(u / 0.35, 1.0, (dur - u) / 0.35)) if kind else 0.0
    shake, gasl = shake * (1 - env), gasl * (1 - env)       # an experiment quiets the simmer -- gently
    jx = math.sin(now * 42) * 2.0 * shake
    tilt = 0.0
    if kind == "shake":                                     # rattled hard, the liquid sloshing
        k = _bump(u, 0, dur)
        jx += math.sin(u * 38) * 3 * k
        tilt = math.sin(u * 14) * 3.5 * k
    cx = round(_X + jx)
    look, mix, level = "shimmer", 0.0, _LIQ
    if kind == "dose":                                      # the drop lands: a change spreads through it
        look, mix = ("shimmer" if int(u * 12) % 2 else "dark"), _bump(u, 0.85, dur)
    elif kind == "foam":
        mix = env
    elif kind == "freeze":                                  # ice spreading through, then thawing back out
        look, mix = "ice", smoothstep(min((u - 0.3) / 0.7, 1.0, (dur - 0.3 - u) / 0.6))
    blown = kind == "boom" and 0.12 <= u < 2.2
    if kind == "boom" and u >= 2.2:                       # refilled from the bottom up
        level = _BOT - (_BOT - _LIQ) * smoothstep((u - 2.2) / 0.5)
    haze = Image.new("L", (W, H))
    if kind == "glow":                                      # light spilling round the tube, pulsing
        soft_spot(haze, cx, (_TOP + _BOT) / 2, 14 + 4 * math.sin(u * 9), 18, 0.55 * _bump(u, 0, dur))
    if kind == "boom" and u < 1.6:                          # the blast's smoke, billowing up and away
        f = u / 1.6
        for j in range(4):
            soft_spot(haze, cx - 4 - j * 3 * (1 + f), _TOP - 2 - 16 * f - j * 3, 4 + 7 * f, 3 + 6 * f, 0.8 * (1 - f), add=True)
    if kind == "foam" and u > 0.6:                          # a wisp of smoke off the froth
        f = (u - 0.6) / (dur - 0.6)
        soft_spot(haze, cx - 2 * f, _TOP - 8 - 12 * f, 2 + 3 * f, 2 + 3 * f, 0.4 * (1 - f))
    img.paste(1, (0, 0), halftone(haze))
    for gy in (42, 48, 54):                                 # the glass's graduation marks
        d.line([cx - _HW - 2, gy, cx - _HW - 1, gy], fill=1)
    if not blown:                                           # the glass
        d.line([cx - _HW, _TOP, cx - _HW, _BOT - _HW], fill=1)
        d.line([cx + _HW, _TOP, cx + _HW, _BOT - _HW], fill=1)
        d.arc([cx - _HW, _BOT - 2 * _HW, cx + _HW, _BOT], 0, 180, fill=1)
    else:                                                   # sooty, cracked glass
        for y in range(_TOP, _BOT - _HW, 3):
            d.point((cx - _HW, y), fill=1)
            d.point((cx + _HW, y + 1), fill=1)
        d.arc([cx - _HW, _BOT - 2 * _HW, cx + _HW, _BOT], 20, 160, fill=1)
    if not blown:
        _liquid(d, cx, level, tilt, look, mix, int(now * 10))
    _extra(d, kind, u, dur, cx, now)
    fizz = {"dose": _bump(u, 0.85, dur), "pop": smoothstep(u / 0.5) * (1 - smoothstep((u - 0.7) / 0.4)),
            "foam": env, "shake": env}.get(kind, 0.0)       # how hard it's fizzing, easing in and out
    if not blown:                                           # bubbles: a steady simmer, and a fast fizz
        for i in range(7):                                  # that swells in over it -- never a jump
            fast = i >= 3
            bt = (now * ((0.6 + i * 0.17) * (2.8 if fast else 1.0)) + i * 0.31) % 1.0
            by = (_BOT - _HW) - bt * (_BOT - _HW - level)
            bx = cx + math.sin(now * (5 if fast else 3) + i * 2) * (_HW - 2.5)
            r = (0.8 + (i % 2)) * (fizz if fast else bubl * (1 - env) + env)
            if r > 0.45:
                d.ellipse([bx - r, by - r, bx + r, by + r], fill=0)
    cap = _cap_at(kind, u, dur, cx)
    if cap is not None:                                     # the stopper, tumbling when it's out
        x, y = cap
        spin = math.sin(u * 14) * 2 if kind == "pop" and 0.7 <= u < 1.7 else 0
        d.polygon([(x - _HW - 1, y + spin), (x + _HW + 1, y - spin), (x + _HW + 1, y + 4 - spin), (x - _HW - 1, y + 4 + spin)], fill=1)
        d.line([x - _HW - 1, y + 2, x + _HW + 1, y + 2], fill=0)
    if kind == "pop" and 0.6 <= u < 0.95:                   # the gas bursting out of the mouth
        f = (u - 0.6) / 0.35
        for a in (-50, -70, -90, -110, -130):
            c, sn = math.cos(math.radians(a)), math.sin(math.radians(a))
            d.line([cx + c * (3 + 8 * f), _TOP - 2 + sn * (3 + 8 * f), cx + c * (6 + 12 * f), _TOP - 2 + sn * (6 + 12 * f)], fill=1)
    if kind == "dose":                                      # the dropper reaching in, one drop falling
        k = smoothstep(min(u / 0.4, 1.0, (dur - u) / 0.4))
        tx, ty = cx - 1, _TOP - 14 - 20 * (1 - k)
        d.rectangle([tx - 5, ty - 10, tx + 5, ty + 2], fill=0)
        d.ellipse([tx - 3, ty - 9, tx + 3, ty - 4], fill=1)
        d.rectangle([tx - 1, ty - 4, tx + 1, ty + 1], outline=1)
        if 0.6 <= u < 0.9:
            fy = ty + 2 + (_LIQ - ty - 2) * ((u - 0.6) / 0.3) ** 2
            d.ellipse([tx - 1, fy - 1, tx + 1, fy + 1], fill=1)
    if kind == "foam":                                      # froth heaped over the rim, dribbling down
        k = smoothstep(min(u / 0.5, 1.0, (dur - u) / 0.4))
        for j in range(6):
            f = (now * 0.9 + j * 0.17) % 1.0
            bx = cx + (j - 2.5) * 1.8 + math.sin(now * 3 + j) * 0.8
            by = _TOP - 1 - (3 + 3 * math.sin(math.pi * f)) * k
            d.ellipse([bx - 1.4, by - 1.4, bx + 1.4, by + 1.4], outline=1)
        for side in (-1, 1):
            d.point((cx + side * (_HW + 1), _TOP + ((u * 7 + side) % 12) * k), fill=1)
    if kind == "boom" and u < 0.14:                         # the flash
        for a in range(0, 360, 30):
            c, sn = math.cos(math.radians(a)), math.sin(math.radians(a))
            d.line([cx + c * 4, _TOP + 6 + sn * 4, cx + c * 14, _TOP + 6 + sn * 12], fill=1)
    if kind == "glow" and 0.5 < u < dur - 0.1:              # a sparkle off the glowing glass
        r = round(3 * _bump(u, 0.5, dur - 0.1))
        for j in range(1, r + 1):
            for dx, dy in ((j, 0), (-j, 0), (0, j), (0, -j)):
                flip(d, cx - 9 + dx, _TOP - 3 + dy)
    if gasl > 0.05:                                         # thin gas wisps while it simmers and vents
        for mx, wdt, spd, off in ((cx - 2, 1, 0.33, 0.0), (cx + 3, 2, 0.25, 0.55)):
            p = (now * spd + off) % 1.0
            ln = (3 + min(p / 0.82, 1.0) * 21) * gasl
            lift = max(0.0, (p - 0.82) / 0.18) * (ln + 8)
            d.line([(mx + math.sin(f * 3.6 + now * 1.8) * (0.5 + f * 2.6), (_TOP - 4 - lift) - f * ln)
                    for f in (j / 7 for j in range(8))], fill=1, width=wdt, joint="curve")


def _extra(d, kind, u, dur, cx, now):
    """The newer experiments: smoke rings, crystals, frost, a critter, a floating bubble, the lens."""
    if kind == "rings":                                     # smoke rings puffed out, drifting off toward Pip
        for j in range(3):
            f = (u - 0.3 - j * 0.45) / 1.3
            if 0 <= f < 1 and (f < 0.8 or int(u * 20) % 2):
                rx, ry = 2 + 4 * f, 1 + 1.6 * f
                x, y = cx - 2 - 26 * f, _TOP - 6 - 14 * f + math.sin(f * 6) * 1.5
                d.ellipse([x - rx, y - ry, x + rx, y + ry], outline=1)
    elif kind == "crystals":                                # spikes growing up through the liquid, a glint
        k = smoothstep(min(u / 1.0, 1.0, (dur - u) / 0.5))
        for j, (bx, ang) in enumerate(((cx - 3, 70), (cx - 1, 95), (cx + 1, 80), (cx + 3, 110), (cx, 60))):
            ln = (6 + 4 * rand(j, 3)) * k
            a = math.radians(ang)
            d.line([bx, _BOT - 3, bx + math.cos(a) * ln, _BOT - 3 - math.sin(a) * ln], fill=0)
        if 1.0 < u < 1.6:
            r = round(2.5 * _bump(u, 1.0, 1.6))
            for j in range(1, r + 1):
                for dx, dy in ((j, 0), (-j, 0), (0, j), (0, -j)):
                    flip(d, cx + 1 + dx, _LIQ + 4 + dy)
    elif kind == "freeze":                                  # frost creeping up the glass, then drips as it thaws
        k = smoothstep(min(u / 0.7, 1.0, (dur - u) / 0.6))
        for y in range(round(_BOT - (_BOT - _TOP) * k), _BOT - 2, 2):
            for side in (-1, 1):
                fx = cx + side * (_HW + 1 + (y // 2) % 2)
                d.point((fx, y), fill=1)
                if (y // 2) % 3 == 0:
                    d.point((fx + side, y - 1), fill=1)
        if u > dur - 0.6:                                   # thawing: a drip running down
            d.point((cx - _HW - 1, _TOP + 6 + 14 * (u - dur + 0.6) / 0.6), fill=1)
    elif kind == "critter":                                 # a little goo blob peeks out, blinks at Pip, ducks
        k = smoothstep(min((u - 0.2) / 0.3, 1.0, (dur - 0.3 - u) / 0.3))
        if k > 0.05:
            top = _TOP - 1 - 9 * k                          # poking up out of the mouth
            d.chord([cx - 4, top, cx + 4, top + 8], 180, 360, fill=1)
            d.rectangle([cx - 4, top + 4, cx + 4, _TOP + 4], fill=1)   # its body, down in the mouth
            blink = 0.9 < u < 1.0 or 1.5 < u < 1.58
            for ex in (cx - 2, cx + 1):                     # its eyes, looking left at Pip
                if blink:
                    d.line([ex - 1, top + 3, ex, top + 3], fill=0)
                else:
                    d.rectangle([ex - 1, top + 2, ex, top + 3], fill=0)
    elif kind == "bubble":                                  # a big bubble swells, floats off, pops by Pip's eye
        if 0.3 <= u < 0.9:                                  # swelling at the mouth
            r = 1 + 3 * (u - 0.3) / 0.6
            d.ellipse([cx - r, _TOP - 2 - 2 * r, cx + r, _TOP - 2], outline=1)
        elif 0.9 <= u < 2.0:
            f = (u - 0.9) / 1.1
            x, y = cx - 14 * f - 4 * math.sin(f * 3), _TOP - 10 - 10 * math.sin(f * 2.4) + math.sin(u * 7) * 1.5
            r = 4 + 0.6 * math.sin(u * 11)
            d.ellipse([x - r, y - r * 0.9, x + r, y + r * 0.9], outline=1)
            d.point((x - r * 0.4, y - r * 0.4), fill=1)     # its highlight
        elif u < 2.3:                                       # pop!
            f = (u - 2.0) / 0.3
            for a in range(0, 360, 45):
                c, sn = math.cos(math.radians(a)), math.sin(math.radians(a))
                flip(d, cx - 14 + c * (3 + 5 * f), _TOP - 10 + sn * (3 + 5 * f))
    elif kind == "lens":                                    # a magnifying glass slides up to look closer
        k = smoothstep(min(u / 0.5, 1.0, (dur - u) / 0.5))
        lx, ly = cx - 1, _LIQ + 6 + 30 * (1 - k)
        d.ellipse([lx - 8, ly - 8, lx + 8, ly + 8], fill=0, outline=1)
        d.ellipse([lx - 7, ly - 7, lx + 7, ly + 7], outline=1)
        d.line([lx + 5, ly + 5, lx + 11, ly + 11], fill=1, width=3)   # the handle
        for j in range(3):                                  # magnified: big lazy bubbles
            f = (now * 0.5 + j * 0.33) % 1.0
            bx, by = lx - 3 + j * 3, ly + 5 - 10 * f
            if (bx - lx) ** 2 + (by - ly) ** 2 < 30:
                d.ellipse([bx - 1.5, by - 1.5, bx + 1.5, by + 1.5], outline=1)
        wig = math.sin(now * 6)                             # and a tiny germ wriggling in there
        d.line([lx - 3, ly + wig, lx - 1, ly - wig, lx + 1, ly + wig], fill=1)


# -- Pip's eyes ----------------------------------------------------------------------------------------
def _focus(now):
    """0..1 how hard Pip's studying the tube: spells of close study in the lulls, and the build-up of
    each experiment -- easing in and out -- but wide open (0) at a pop, a blast or a glow."""
    kind, u, dur = _event(now)
    idle = max(0.0, min(1.0, (math.sin(now * 0.37) + math.sin(now * 0.83 + 1.2) - 0.4) / 0.6))
    if kind is None:
        return idle
    ease = smoothstep(min(u / 0.35, 1.0, (dur - u) / 0.35))
    return {"dose": 0.9 * ease, "foam": 0.75 * ease, "shake": 0.5 * ease,
            "pop": 0.9 * smoothstep(u / 0.4) * (1 - smoothstep((u - 0.55) / 0.15)),   # bracing... then wide
            "glow": 0.0, "boom": 0.0, "rings": 0.4 * ease, "crystals": 0.7 * ease, "freeze": 0.35 * ease,
            "critter": 0.0, "bubble": 0.5 * ease * (1 - smoothstep((u - 1.9) / 0.1)), "lens": 1.0 * ease,
            }[kind] + idle * (1 - ease)


def _eyes(d, x, y, w, h, right, now):
    """Plain eyes, narrowing as Pip focuses: flat lids closing in from top and bottom into a squint."""
    k = _focus(now)
    if k > 0.02:
        lids(d, x, y, w, h, top=0.24 * k, bottom=1 - 0.24 * k)


def _pose(now):   # eyes on the tube; lean in to a dose; follow the stopper; jolt at a blast
    kind, u, dur = _event(now)
    gx, gy, h = 2 + math.sin(now * 1.6) * 1.2, 5 + math.sin(now * 1.1) * 1.5, 0.95   # glancing its way, clear of it
    gx += 1.5 * _focus(now)                                 # studying it: a little lean toward it
    if kind == "shake":
        gx += math.sin(u * 38) * 1.2 * _bump(u, 0, dur)
    elif kind == "pop":
        cap = _cap_at(kind, u, dur, _X)
        k = _bump(u, 0.6, 1.8)
        gx, gy = gx + (cap[0] - _X) * 0.25 * k, gy + (cap[1] - _TOP) * 0.3 * k
        h += 0.15 * _bump(u, 0.6, 1.0)                      # startled wide
    elif kind == "glow":
        h += 0.08 * _bump(u, 0, dur)
    elif kind == "boom":
        k = _bump(u, 0, 0.7)
        h, gy, gx = h + 0.15 * k, gy - 3 * k, gx - 3 * k
    elif kind == "critter":                                 # wait -- is that looking at me?
        k = _bump(u, 0.4, dur - 0.2)
        h, gx = h + 0.15 * k, gx - 2 * _bump(u, 0.4, 0.8)
    elif kind == "freeze":                                  # brr: a shiver
        gx += math.sin(u * 45) * 0.8 * _bump(u, 0.4, dur - 0.3)
    elif kind == "bubble" and 0.9 <= u < 2.0:               # following the bubble over
        f = (u - 0.9) / 1.1
        gx, gy = gx - 4 * f, gy - 3 * math.sin(f * 2.4)
    elif kind == "bubble" and 2.0 <= u < 2.35:              # it pops right by Pip's eye: a blink
        h -= 0.5 * _bump(u, 2.0, 2.35)
    return gx, gy, h


ACTION = Action("testing", mood="neutral", pose=_pose, overlay=_overlay, eyes=_eyes)


if __name__ == "__main__":
    seen = set()
    for s in range(300):
        plan = _plan(s)
        seen |= {k for _, k, _ in plan}
        assert plan and plan[-1][0] + plan[-1][2] <= _STRETCH - 0.4, "every experiment ends inside its stretch"
        assert all(a[0] + a[2] < b[0] for a, b in zip(plan, plan[1:])), "one at a time, a lull between"
        assert all(a[1] != b[1] for a, b in zip(plan, plan[1:])), "never the same twice running"
    assert seen == {k for k, _, _ in _KINDS}, seen
    for kind, _, dur in _KINDS:                             # the stopper always ends back in the mouth
        x, y = _cap_at(kind, dur - 1e-6, dur, _X)
        assert abs(x - _X) < 0.5 and abs(y - (_TOP - 4)) < 0.5, f"{kind}: stopper home"
    fs = [_focus(i / 30) for i in range(30 * 120)]          # the eyes ease, never snap
    assert max(abs(b - a) for a, b in zip(fs, fs[1:])) < 0.3, "focus eases (only the pop startles it open fast)"
    assert min(fs) == 0 and max(fs) > 0.8, "sometimes plain, sometimes deep in focus"
    print("testing ok")
