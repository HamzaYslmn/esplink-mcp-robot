"""KO -- knocked out cold, the cartoon way: each eye is an inked X (x_x) -- brush strokes, thick
where they cross and tapering to rounded tips -- the two slumped a touch low and rocking slowly out of
level. Over Pip's head a tilted ring of sparkles circles, each trailing a short comet tail: the near
side big and twinkling, the far side small, and the whole ring tips with the rock. Now and then an
X gives a last twitch."""
import math

from ..primitives import rand
from ..spec import Mood

_EYES = ((41, 34), (87, 34))                      # resting eye centres, a hair low: slumped
_ARM, _FAT, _TIP = 13.0, 3.0, 1.8                 # X half-span, stroke half-width at the cross / tips
_ORBIT = (64, 7, 34, 4.5)                         # sparkle ring: centre x, y, radius x, y
_N_STARS, _SPIN = 3, 2.2                          # sparkles, rad/s
_TWITCH = 4.0                                     # s per twitch window


def _x(d, cx, cy, arm, rot):
    """Four tapered half-strokes: thick where they cross, easing to round tips -- an inked X."""
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2 + rot
        ux, uy = math.cos(a), math.sin(a)
        px, py = -uy, ux
        tx, ty = cx + ux * arm, cy + uy * arm
        d.polygon([(cx + px * _FAT, cy + py * _FAT), (tx + px * _TIP, ty + py * _TIP),
                   (tx - px * _TIP, ty - py * _TIP), (cx - px * _FAT, cy - py * _FAT)], fill=1)
        d.ellipse([tx - _TIP, ty - _TIP, tx + _TIP, ty + _TIP], fill=1)


def _sparkle(d, x, y, r):                         # 4-point star: long cross arms, short diagonal glints
    if r < 1.5:
        d.point([(x, y)], fill=1)
        return
    r = round(r)
    d.line([(x - r, y), (x + r, y)], fill=1)
    d.line([(x, y - r), (x, y + r)], fill=1)
    if r >= 3:
        d.point([(x - 1, y - 1), (x + 1, y - 1), (x - 1, y + 1), (x + 1, y + 1)], fill=1)


def _decor(d, W, H, now, ox=0.0, oy=0.0):
    j = int(now / _TWITCH)
    t0 = j * _TWITCH + rand(j, 3) * (_TWITCH - 0.4)
    tw_eye = int(rand(j, 5) * 2) if rand(j, 4) < 0.5 and t0 <= now < t0 + 0.35 else -1
    rock = math.sin(now * 0.9)                    # the slumped seesaw, -1..1
    for i, (cx, cy) in enumerate(_EYES):
        jerk = 0.12 * math.sin(now * 60) if i == tw_eye else 0.0   # the twitch: a quick shudder
        _x(d, cx + ox, cy + oy + (1.3 if i else -1.3) * rock, _ARM - 2 * (i == tw_eye), 0.05 * rock + jerk)
    mx, my, rx, ry = _ORBIT
    for k in range(_N_STARS):
        a0 = now * _SPIN + k * 2 * math.pi / _N_STARS
        for n in range(4, -1, -1):                # comet tail first, the sparkle on top
            a = a0 - n * 0.16
            depth = 0.5 + 0.5 * math.sin(a)       # 1 = near side, 0 = far side
            x = round(mx + ox + rx * math.cos(a))
            y = round(my + ry * math.sin(a) + 2.2 * rock * math.cos(a))   # the ring tips with the rock
            if n:
                if n <= 1 + 2 * depth:            # longer tails up front
                    d.point([(x, y)], fill=1)
            else:
                twinkle = 0.8 + 0.2 * math.sin(now * 11 + k * 2.1)
                _sparkle(d, x, y, (1.4 + 3.6 * depth) * twinkle)


MOOD = Mood("dead", bare=True, still=True, decor=_decor)
