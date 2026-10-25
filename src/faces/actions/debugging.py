"""Debugging -- a bug hunt. A little beetle wanders the floor under Pip's eyes the way a real bug does:
scuttling a bit, stopping to twitch its feelers, turning, scuttling on, its stubby legs stepping only
as it moves. Pip watches it, narrow-eyed, and goes for it with a fly swatter swung from off-screen:
the swatter peeks in over the top, its shadow sliding in under the bug, a wind-up -- and it swings
down hard, trailing a smear, the mesh paddle flexing on the floor and wobbling as dust flies.

Each round the bug pulls its own tricks:
  dodge     darts clear a split second before the slap (Pip jolts, annoyed)
  double    two slaps in quick succession -- it dodges both, one way then the other
  zigzag    a frantic zigzag sprint
  taunt     stops, turns to face Pip and does a cheeky little hop-dance
  play dead flips on its back, legs wiggling, as the swatter lines up -- Pip hesitates, the swatter
            pulls back, and the bug flips over and scarpers
  fly       spreads its wings and buzzes a loop round Pip's head before landing again
  hide      runs off the edge of the screen and sneaks back in from the other side
  multiply  splits off a second bug that scurries away -- fix one, find two
-- and at last the slap lands: the bug's squashed flat, crumbles into sparkles, a tick pops up --
fixed -- and the next bug wanders in.

Self-check: `cd src && uv run python -m faces.actions.debugging`."""
import math
from functools import cache

from PIL import Image, ImageDraw, ImageFilter

from ..primitives import flip, frame, rand, smoothstep
from ..spec import Action

_ROUND = 12.0                  # s per hunt (then the next bug)
_G = 59                        # the floor: y the bug's feet stand on
_AIM, _SLAM, _HOLD, _LIFT = 0.7, 0.08, 0.2, 0.35   # s: the swatter lines up, swings, sits, swings away
_FLY = 1.8                     # s a flight takes
_SPLAT = 1.6                   # s from the catch to the next bug: squash, crumble, tick
_SS = 4                        # supersample factor for the swatter
_NEED = {"dodge": 1.4, "double": 2.8, "zigzag": 1.3, "taunt": 1.6, "dead": 2.7, "fly": 2.2,
         "hide": 5.6, "multiply": 1.3}   # s each trick can take, at most


# -- the plan: the bug's path (keyframes) and the swats ------------------------------------------------
@cache
def _plan(s):
    """-> (bug keyframes ((time, x, y, mode), ...), swats ((slam time, x, 'miss'|'feint'|'hit', aim s),
    ...), clone (time, x, exit x) | None, tricks played). Between keyframes the bug eases; mode is
    'walk', 'dart', 'fly', 'off', or -- held in place -- 'dance' / 'dead'."""
    x = 64 + (-76 if rand(s, 1) < 0.5 else 76)              # in from an edge
    keys, t, i = [(0.0, x, _G, "walk")], 0.0, 0
    swats, clone, events = [], None, []
    pool = list(_NEED)

    def go(to, speed, mode="walk", y=_G):
        nonlocal t, x
        t += max(0.12, abs(to - x) / speed)
        x = to
        keys.append((t, x, y, mode))

    def rest(d, mode="walk"):
        nonlocal t
        t += d
        keys.append((t, x, _G, mode))

    away = lambda d: x + (d if x < 64 else -d)              # toward the roomier side

    go(20 + rand(s, 2) * 88, 30)
    while True:
        i += 1
        left = _ROUND - _SPLAT - 1.2 - t                    # what's left before the final slap
        fits = [e for e in pool if _NEED[e] < left]
        if left < 1.4:
            break
        if rand(s, i, 1) < 0.35 or not fits:                # wander: a scuttle and a pause
            if left < 2.8:
                break
            go(min(112, max(14, x + (rand(s, i, 2) - 0.5) * 70)), 18 + rand(s, i, 3) * 22)
            rest(0.2 + rand(s, i, 4) * 0.7)
            continue
        ev = fits[int(rand(s, i, 5) * len(fits))]
        pool.remove(ev)
        events.append(ev)
        if ev == "dodge":                                   # Pip swats; the bug darts clear
            rest(_AIM)
            swats.append((t + 0.12, x, "miss", _AIM))
            go(away(30), 120, "dart")
            rest(0.5)
        elif ev == "double":                                # slap -- dodge -- slap again -- dodge again
            rest(_AIM)
            swats.append((t + 0.12, x, "miss", _AIM))
            go(away(24), 120, "dart")
            rest(0.85)                                      # the swatter swings away, comes straight back
            swats.append((t + 0.12, x, "miss", 0.42))
            go(x - (26 if x > 64 else -26), 120, "dart")
            rest(0.5)
        elif ev == "zigzag":                                # a frantic zigzag sprint
            for k in range(4):
                go(min(114, max(12, x + (14 if k % 2 else -14) * (1 if x < 64 else -1) + 6)), 110, "dart")
            rest(0.4)
        elif ev == "taunt":                                 # a cheeky little hop-dance at Pip
            rest(1.3, "dance")
            rest(0.2)
        elif ev == "dead":                                  # plays dead; Pip hesitates; it scarpers
            swats.append((t + 0.78, x, "feint", 0.7))        # the swatter lines up...
            rest(0.35)
            rest(1.4, "dead")                               # ...and over it goes
            go(away(34), 110, "dart")
            rest(0.4)
        elif ev == "fly":                                   # up, a loop round Pip's head, down again
            x0, t0 = x, t
            for k in range(1, 9):
                a = k / 8 * math.tau
                lift = math.sin(math.pi * k / 9)
                keys.append((t0 + _FLY * k / 9, 64 + 46 * math.sin(a + (0 if x0 > 64 else math.pi)) * (0.3 + 0.7 * lift),
                             _G - 8 - 34 * lift - 6 * math.sin(a * 2), "fly"))
            t = t0 + _FLY
            x = min(112, max(14, 64 + (64 - x0) * 0.6))
            keys.append((t, x, _G, "fly"))
            rest(0.3)
        elif ev == "hide":                                  # off one edge, back in from the other
            edge = -12 if x < 64 else 140
            go(edge, 60)
            rest(0.8)
            x = 140 if edge < 0 else -12
            t += 0.01
            keys.append((t, x, _G, "off"))
            go(20 + rand(s, i, 6) * 88, 45)
        else:                                               # a second bug splits off and scurries away
            rest(0.3)
            clone = (t, x, -14 if x < 64 else 142)
            rest(0.9)
    rest(0.4)                                               # it stops -- Pip's had enough
    rest(_AIM)
    swats.append((t, x, "hit", _AIM))                       # the slap that lands
    return tuple(keys), tuple(swats), clone, tuple(events)


def _round(now):
    """(seconds into this hunt, its plan)."""
    T, seed = getattr(now, "t", now), getattr(now, "seed", 0)
    k, t = divmod(T, _ROUND)
    return t, _plan(int(rand(seed, k) * 1e6))


def _bug_at(t, keys):
    """(x, y, facing -1/1, mode, how far it's walked) of the bug at t -- easing between keyframes."""
    prev = keys[0]
    for k in keys[1:]:
        if t < k[0]:
            f = (t - prev[0]) / (k[0] - prev[0])
            e = f if k[3] in ("dart", "fly") else smoothstep(f)
            x = prev[1] + (k[1] - prev[1]) * e
            y = prev[2] + (k[2] - prev[2]) * e
            face = 1 if k[1] >= prev[1] else -1
            moving = k[1] != prev[1] or k[2] != prev[2]
            return x, y, face, k[3] if moving or k[3] in ("dance", "dead") else "rest", x
        prev = k
    return prev[1], prev[2], 1, "rest", prev[1]


# -- the bug -------------------------------------------------------------------------------------------
def _bug(d, x, y, face, mode, step, now, flat=0.0):
    """A little beetle in profile: a domed, spotted shell, a head with feelers, three stubby legs
    stepping as it goes (still when it stops, feelers twitching), wings buzzing when it flies, a hop
    when it dances, legs in the air when it plays dead -- or squashed flat."""
    if flat:                                                # squashed: a flat splat, legs splayed
        w = 7 + 3 * flat
        d.ellipse([x - w, y - 2, x + w, y], fill=1)
        for k in (-1, 1):
            d.line([x + k * w, y - 1, x + k * (w + 3), y - 3], fill=1)
            d.line([x + k * (w - 3), y - 1, x + k * (w - 1), y - 4], fill=1)
        return
    if mode == "dead":                                      # on its back, legs kicking at the air
        d.chord([x - 6, y - 6, x + 6, y + 1], 0, 180, fill=1)
        d.line([x - 5, y - 3, x + 5, y - 3], fill=1)
        for j in range(3):
            lx = x - 4 + j * 4
            d.line([lx, y - 3, lx + math.sin(now * 22 + j * 2) * 1.5, y - 6], fill=1)
        d.ellipse([x + 6, y - 3, x + 9, y], fill=1)
        return
    if mode == "dance":                                     # hop, hop, turn
        y -= round(2.5 * abs(math.sin(now * 9)))
        face = 1 if int(now * 4) % 2 else -1
    d.chord([x - 6, y - 10, x + 6, y - 2], 180, 360, fill=1)    # the dome
    d.rectangle([x - 5, y - 6, x + 5, y - 3], fill=1)            # its belly
    for sx in (-2, 2):                                      # spots on the shell
        d.point((x + sx, y - 8), fill=0)
    hx = x + face * 7
    d.ellipse([hx - 2, y - 6, hx + 2, y - 2], fill=1)
    tw = math.sin(now * 13) * (1.2 if mode in ("rest", "dance") else 0.3)
    d.line([hx + face, y - 5, hx + face * 4, y - 9 + tw], fill=1)          # feelers
    d.line([hx, y - 5, hx + face * 2, y - 9 - tw], fill=1)
    if mode == "fly":                                       # wings blurring
        up = int(now * 30) % 2
        d.ellipse([x - 5, y - 14 - 2 * up, x + 1, y - 9], outline=1)
        d.ellipse([x - 1, y - 13 + up, x + 6, y - 9], outline=1)
    for j in range(3):                                      # stubby legs; the gait follows the distance walked
        lx = x - 4 + j * 4
        swing = math.sin(step * 0.9 + j * 2.1) * 1.2 if mode != "fly" else 0.6
        d.line([lx, y - 3, lx + swing, y], fill=1)


# -- the swatter ---------------------------------------------------------------------------------------
def _pivot(x):
    """Where the swatter's swung from: off-screen above, on the side nearer the target."""
    return (-30.0, -26.0, 1) if x < 64 else (158.0, -26.0, -1)


def _swing(sw, u):
    """(elevation below the horizon toward the target, impact 0..1) of the swatter, u s after its slam:
    swings in to peek over the top, winds up, slams down, wobbles, swings away -- or, on a feint,
    peeks and pulls back."""
    x, kind, aim = sw[1], sw[2], sw[3]
    px, py, side = _pivot(x)
    L = math.hypot(x - px, _G - 7 - py)
    hit = math.atan2(_G - 7 - py, abs(x - px))
    peek = math.asin((4 - py) / L)                          # its paddle just showing at the top
    hide = math.asin((-16 - py) / L)                        # out of sight
    if u < -_SLAM:                                          # lining up, then a wind-up
        f = (u + _SLAM + aim) / aim
        a = hide + (peek - hide) * smoothstep(f / 0.6)
        return a - 0.12 * smoothstep((f - 0.75) / 0.25) if kind != "feint" else a, 0.0
    if kind == "feint":                                     # pulls back without swinging
        return peek + (hide - peek) * smoothstep(u / 0.4), 0.0
    if u < 0:                                               # the swing: accelerating into the floor
        start = peek - 0.12
        return start + (hit - start) * ((u + _SLAM) / _SLAM) ** 2, 0.0
    if u < _HOLD:                                           # flat on the floor, wobbling
        return hit - 0.04 * math.sin(u * 60) * math.exp(-u * 12), max(0.0, 1 - u / 0.1)
    return hit + (hide - hit) * smoothstep((u - _HOLD) / _LIFT), 0.0


def _paddle(g, x, ang, impact):
    """Draw the swatter at elevation `ang` on the supersampled layer: a wire handle with a V neck, and
    a rounded mesh paddle -- squashing flat and spreading on impact."""
    px, py, side = _pivot(x)
    L = math.hypot(x - px, _G - 7 - py)
    dx, dy = side * math.cos(ang), math.sin(ang)            # along the handle, out to the paddle
    nx, ny = -dy, dx                                        # across the paddle
    cx, cy = px + dx * L, py + dy * L
    a, w = 7.5 * (1 - 0.25 * impact), 8.5 * (1 + 0.12 * impact)
    pt = lambda u, v: ((cx + dx * u + nx * v) * _SS, (cy + dy * u + ny * v) * _SS)
    rim = [pt(-a + 1.5, -w), pt(a - 1.5, -w), pt(a, -w + 1.5), pt(a, w - 1.5), pt(a - 1.5, w),
           pt(-a + 1.5, w), pt(-a, w - 1.5), pt(-a, -w + 1.5)]
    g.line([pt(-a - 4, 0), ((px + dx * 20) * _SS, (py + dy * 20) * _SS)], fill=255, width=2 * _SS)   # handle
    g.line([pt(-a, -4), pt(-a - 4, 0), pt(-a, 4)], fill=255, width=_SS)       # the wire neck
    g.polygon(rim, fill=255)
    for k in (-5, -2, 1, 4):                                # the mesh
        g.line([pt(-a + 1.5, k + 0.5), pt(a - 1.5, k + 0.5)], fill=0, width=_SS)
        g.line([pt(k * a / 7.5 + 0.5, -w + 1.5), pt(k * a / 7.5 + 0.5, w - 1.5)], fill=0, width=_SS)


def _swat_state(t, swats):
    """(the swat under way | None, seconds relative to its slam) -- from lining up to swung away."""
    for sw in swats:
        u = t - sw[0]
        if -sw[3] - _SLAM <= u < _HOLD + _LIFT:
            return sw, u
    return None, 0.0


def _draw_swatter(img, W, H, sw, u):
    lay = Image.new("L", (W * _SS, H * _SS))
    g = ImageDraw.Draw(lay)
    ang, impact = _swing(sw, u)
    if sw[2] != "feint" and -_SLAM <= u < 0.03:             # speed lines trailing the paddle's swing
        px, py, side = _pivot(sw[1])
        L = math.hypot(sw[1] - px, _G - 7 - py)
        back = _swing(sw, max(u - 0.05, -_SLAM))[0]
        for r in (L - 6, L + 1, L + 8):
            arc = [((px + side * math.cos(a) * r) * _SS, (py + math.sin(a) * r) * _SS)
                   for a in (back + (ang - back) * k / 6 for k in range(6))]
            g.line(arc, fill=255, width=_SS)
    _paddle(g, sw[1], ang, impact)
    small = lay.resize((W, H), Image.BOX).point(lambda v: 255 if v >= 110 else 0)
    img.paste(0, (0, 0), small.filter(ImageFilter.MaxFilter(3)).convert("1"))   # a black rim
    img.paste(1, (0, 0), small.convert("1"))


# -- the scene -----------------------------------------------------------------------------------------
def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    img = frame(d)
    if img is None:
        return
    t, (keys, swats, clone, _) = _round(now)
    bx, by, face, mode, step = _bug_at(t, keys)
    catch = swats[-1][0]
    sw, u = _swat_state(t, swats)
    if sw and u < (0.4 if sw[2] == "feint" else 0):         # the shadow, growing as it lines up
        k = smoothstep((u + sw[3] + _SLAM) / (sw[3] + _SLAM))
        if sw[2] == "feint" and u > 0:
            k *= 1 - u / 0.4
        w = 5 + 7 * k
        for j in range(0, 2 * round(w), 2):
            d.point((sw[1] - w + j, _G + 1), fill=1)
    if t < catch:
        _bug(d, bx, by, face, mode, step, now)
    else:                                                   # squashed, crumbling to sparkles, then a tick
        a = t - catch
        if a < 0.7 or (a < 1.0 and int(a * 20) % 2):
            _bug(d, bx, _G, face, mode, step, now, flat=min(1.0, a / 0.1))
        if 0.6 < a < 1.3:
            for i in range(5):
                f = (a - 0.6) / 0.7
                if int(a * 15 + i) % 3:
                    flip(d, bx + (rand(i, 1) - 0.5) * 16, _G - 3 - f * (8 + 8 * rand(i, 2)))
        if 0.9 < a < _SPLAT - 0.1:
            k = smoothstep((a - 0.9) / 0.2)
            cy = _G - 8 - 3 * k
            d.line([bx - 3, cy, bx - 1, cy + 2, bx + 4, cy - 3], fill=1, width=1 if a < 1.0 else 2)
    if clone and clone[0] <= t < clone[0] + 1.2:            # the second bug scurrying off
        f = (t - clone[0]) / 1.2
        cx = clone[1] + (clone[2] - clone[1]) * f ** 1.4
        _bug(d, cx, _G, 1 if clone[2] > clone[1] else -1, "walk", cx, now)
    if sw:
        _draw_swatter(img, W, H, sw, u)
        if sw[2] != "feint" and 0 <= u < 0.25:              # SLAP: dust kicked out both sides, a shake
            for k in (-1, 1):
                for j in range(3):
                    f = u / 0.25
                    flip(d, sw[1] + k * (11 + 10 * f + j * 3), _G - 1 - j * 2 - 4 * f)
            if u < 0.08:
                snap = img.copy()
                d.rectangle([0, 0, W - 1, H - 1], fill=0)
                img.paste(snap, (0, 2 if int(u * 50) % 2 else -1))


def _pose(now):   # eyes narrowed on the bug; lock on while lining up; jolt at a miss; ease off once fixed
    t, (keys, swats, clone, _) = _round(now)
    bx, by, _, mode, _ = _bug_at(t, keys)
    if clone and clone[0] <= t < clone[0] + 1.2:            # wait, there's two?
        f = (t - clone[0]) / 1.2
        bx = bx + (clone[1] + (clone[2] - clone[1]) * f - bx) * math.sin(math.pi * f)
    gx, gy, h = max(-12.0, min(12.0, (bx - 64) * 0.2)), 2 + (by - _G) * 0.12, 0.85
    if mode == "dance":                                     # the cheek of it: a hard squint
        h -= 0.2
    sw, u = _swat_state(t, swats)
    if sw:
        if u < 0:                                           # locking on
            h -= 0.2 * smoothstep((u + sw[3]) / sw[3])
        elif sw[2] == "miss" and u < 0.5:                   # missed! a jolt
            gy -= 2.5 * math.sin(math.pi * u / 0.5)
            h += 0.15 * math.sin(math.pi * u / 0.5)
        elif sw[2] == "feint" and u < 0.6:                  # ...is it dead? a puzzled widen
            h += 0.2 * math.sin(math.pi * u / 0.6)
    if t >= swats[-1][0]:                                   # got it: the eyes ease open
        h += 0.25 * smoothstep((t - swats[-1][0] - 0.8) / 0.4)
    return gx, gy, h


ACTION = Action("debugging", mood="suspicious", pose=_pose, overlay=_overlay)


if __name__ == "__main__":
    seen = set()
    for s in range(400):
        keys, swats, clone, events = _plan(s)
        seen |= set(events)
        assert swats[-1][2] == "hit" and all(k != "hit" for _, _, k, _ in swats[:-1]), "only the last slap lands"
        assert swats[-1][0] + _SPLAT <= _ROUND, "the fix finishes inside the round"
        assert all(a[0] < b[0] for a, b in zip(keys, keys[1:])), "keyframes run forward"
        assert keys[0][1] < -5 or keys[0][1] > 133, "each bug wanders in from off-screen"
        for at, x, kind, aim in swats:
            bx = _bug_at(at, keys)[0]
            if kind == "hit":
                assert abs(bx - x) < 0.5, "the last slap lands on the bug"
            elif kind == "miss":
                assert abs(bx - x) > 10, "a dodge gets clear in time"
        for a, b in zip(swats, swats[1:]):                  # one swat at a time
            assert b[0] - b[3] - _SLAM >= a[0] + _HOLD + _LIFT - 1e-9, "one swat at a time"
        for a, b in zip(keys, keys[1:]):                    # no visible jumps: it only teleports off-screen
            if b[3] == "off":
                assert (a[1] < -5 or a[1] > 133) and (b[1] < -5 or b[1] > 133), "teleports off-screen only"
    assert seen == set(_NEED), f"every trick comes up: {seen}"
    for x in (14, 64, 112):                                 # the swing ends on the target, hidden at both ends
        sw = (1.0, x, "hit", _AIM)
        ang, _ = _swing(sw, 0.0)
        px, py, side = _pivot(x)
        L = math.hypot(x - px, _G - 7 - py)
        assert abs(px + side * math.cos(ang) * L - x) < 0.5, "the paddle lands on the target"
        for u in (-_AIM - _SLAM, _HOLD + _LIFT - 1e-6):
            assert py + math.sin(_swing(sw, u)[0]) * L < -6, "out of sight before and after"
    print("debugging ok")
