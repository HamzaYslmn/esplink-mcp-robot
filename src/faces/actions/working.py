"""At the forge -- working, Tony-Stark-in-the-cave style. A dark shop lit only by the white-hot bar,
whose glow pools round the anvil as a halftone halo that breathes with the heat and flares on every
blow.

Each piece: the bar is swung in glowing from the fire off to the right and onto the anvil, then
worked in a fresh rhythm -- steady blows with ringing taps on the anvil between, tap-tap-BANG, a
flurry, two heavy hits, or a long job where it cools, goes back in the fire to reheat, and comes
back for more. The cross-peen hammer lifts, hangs, and SMASHES down trailing a swoosh -- a star
flash, a shower of streaking sparks, embers drifting up, the bar flattening and stretching. Then the
hammer goes up on the shoulder while Pip looks the bar over as it cools to grey under rising steam,
a glint runs along the finished piece, and it's set aside for the next.

Every piece gets up to two random moments on top:
  ping     a glancing blow rings off the bar and bounces the hammer high (tink!)
  spark    a stray spark flies straight at Pip's eye -- a flinch
  scale    a heavy blow knocks a flake of scale spinning off the bar
  ember    a big ember floats up past Pip's eyes, which follow it up until it winks out
  flip     between blows Pip flips the bar over -- it hops, turns, lands
  inspect  between blows Pip leans in close for a squint at the work
A heavy piece leaves a bead of sweat, which slides down and dries off.

Everything is painted in greys (supersampled, so edges stay smooth at any angle), then halftoned
with an ordered dither -- the 1-bit panel's way of showing light and haze. Everything eases in and
out: lights fade up, steam rises and thins, the eyes glide between beats.

Self-check: `cd src && uv run python -m faces.actions.working`."""
import math

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from ..primitives import flip, frame, halftone, rand, smoothstep, soft_spot
from ..spec import Action

_PIECE = 6.8                   # s per piece: fetch, the blows, the look-over, set it aside
_FETCH = 0.6                   # s to swing the bar from the fire to the anvil
_TRIP = 0.45                   # s each way on a reheat trip
_ASIDE = 0.4                   # s at the end to set the finished piece aside
_SWING, _RECOIL = 0.08, 0.16   # s: smash down / bounce off the bar
_PING = 0.45                   # s a glancing blow's high bounce takes
_TAP = 0.2                     # blows this light are ringing taps: a 'ting', no sparks
_SS = 4                        # supersample factor for the forge art
_GX, _GY, _L = 2, 68, 62       # the grip (off-screen, lower left) and its reach to the head's centre
_REST = 25.0                   # handle angle (deg, y-up) with the head on the bar
_HOVER = _REST + 4             # ...and held just above it between blows
_HEAD = (7.0, 2.8)             # head half-length (across the handle) / half-thickness
_FIRE = (142, 50)              # the fire, off-screen right: where the bar comes from and reheats
_EYE = (41, 32)                # the left eye's centre at rest (the stray spark's target)
_LONG = {"flip": 0.5, "inspect": 0.8, "ember": 2.2, "ping": _PING, "spark": 0.8, "scale": 0.8}   # s each lasts
_STEAM = 1.3                   # s a puff of steam lives
_CLEAR = {"ping", "flip", "inspect"}   # moments that need the hammer to themselves


def _hammer_at(ang):
    """(head centre, handle direction, across-the-handle direction) at a handle angle."""
    a = math.radians(ang)
    ux, uy = math.cos(a), -math.sin(a)
    return (_GX + _L * ux, _GY + _L * uy), (ux, uy), (-uy, ux)


(_hx, _hy), _, (_px, _py) = _hammer_at(_REST)
_AX, _AY = _hx + _HEAD[0] * _px, _hy + _HEAD[0] * _py      # the striking face lands here: the bar's top


# -- the plan: one piece's rhythm, reheat trip and random moments ------------------------------------
def _windup(p):
    """(raised angle deg, lift s, hold s) -- the harder the blow, the higher and longer the wind-up."""
    return _HOVER + 13 + 38 * p, 0.1 + 0.2 * p, 0.04 + 0.3 * p * p


def _rhythm(seed):
    """-> (blows [(time s, power 0..1)], reheat trip (out, back) | None)."""
    j = lambda i: (rand(seed, i) - 0.5) * 0.1
    kind = int(rand(seed) * 5)
    if kind == 0:                                           # steady blows, a ringing tap after each
        blows = [b for i in range(3) for b in ((1.15 + 0.85 * i + j(i), 0.6), (1.45 + 0.85 * i + j(i), 0.15))]
        return blows + [(3.75, 0.7)], None
    if kind == 1:                                           # tap, tap, BANG
        return [(1.0, 0.35), (1.45 + j(1), 0.35), (2.5 + j(2), 1.0)], None
    if kind == 2:                                           # a flurry of taps, then a firm one
        return [(1.0 + 0.36 * i, 0.3) for i in range(5)] + [(3.15 + j(1), 0.8)], None
    if kind == 3:                                           # two heavy hits
        return [(1.45 + j(1), 1.0), (2.75 + j(2), 1.0)], None
    return [(1.1, 0.6), (1.8 + j(1), 0.6), (3.8, 0.7), (4.4, 0.8)], (2.1, 3.3)   # cools, reheats, more


def _make_room(blows, trip, need, seed):
    """Open a pause in the rhythm long enough for a between-blows moment (a flip, a squint):
    -> (blows with the later ones pushed back, when the pause starts) -- or (blows, None) if no fit."""
    if trip:
        return blows, None
    n = len(blows)
    for k in range(n):
        i = (int(rand(seed, 70) * n) + k) % n               # a random spot, else the next that fits
        start = blows[i - 1][0] + _RECOIL + 0.1 if i else _FETCH + 0.15
        _, lift, hold = _windup(blows[i][1])
        room = blows[i][0] - _SWING - lift - hold - 0.1 - start
        push = max(0.0, need + 0.1 - room)
        if blows[-1][0] + push + 1.8 <= _PIECE - _ASIDE:
            return blows[:i] + [(at + push, p) for at, p in blows[i:]], start
    return blows, None


def _plan(seed):
    """-> (blows, trip, moments ((kind, time s), ...)) for one piece: up to two random moments. A
    glancing blow's high bounce, a flip and a squint each need the hammer clear -- at most one of them."""
    blows, trip = _rhythm(seed)
    pool, chosen = list(_LONG), []
    for i in range((0, 1, 1, 2, 2)[int(rand(seed, 50) * 5)]):
        k = pool[int(rand(seed, 51 + i) * len(pool))]
        chosen.append(k)
        pool = [x for x in pool if x != k and not (k in _CLEAR and x in _CLEAR)]
    moments = []
    for k in chosen:                                        # the pause first: it moves the blows
        if k in ("flip", "inspect"):
            blows, at = _make_room(blows, trip, _LONG[k], seed)
            if at is not None:
                moments.append((k, at))
    gaps = [(b, (n[0] if n else 9.9) - b[0]) for b, n in zip(blows, blows[1:] + [None])]
    options = {                                             # each other moment's possible times
        "ping": [b[0] for b, gap in gaps if b[1] >= 0.5 and gap > 0.7],
        "spark": [b[0] for b in blows if b[1] >= 0.5],
        "scale": [b[0] for b in blows if b[1] >= 0.8],
        "ember": [b[0] + 0.15 for b in blows if b[1] >= 0.5 and b[0] + 0.15 + _LONG["ember"] < _PIECE - _ASIDE],
    }
    for i, k in enumerate(chosen):
        if options.get(k):
            moments.append((k, options[k][int(rand(seed, 60 + i) * len(options[k]))]))
    return blows, trip, tuple(moments)


def _piece(now):
    """(seconds into this piece, its plan, 0..1 how far into the cooling look-over)."""
    T, seed = getattr(now, "t", now), getattr(now, "seed", 0)
    k, t = divmod(T, _PIECE)
    plan = _plan(int(rand(seed, k) * 1e6))
    start, end = plan[0][-1][0] + 0.6, _PIECE - _ASIDE
    return t, plan, smoothstep((t - start) / (end - start)) if t > start else 0.0


def _beat(t, blows):
    """(since last blow, last blow|None, until next blow, next blow|None)."""
    last = max((b for b in blows if b[0] <= t), default=None)
    nxt = min((b for b in blows if b[0] > t), default=None)
    return (t - last[0] if last else 9.9), last, (nxt[0] - t if nxt else 9.9), nxt


def _since(t, plan, kind):
    """Seconds into this piece's moment of `kind` while it lasts, else None."""
    for k, at in plan[2]:
        if k == kind and at <= t < at + _LONG[k]:
            return t - at
    return None


def _bump(x, dur):
    """0 -> 1 -> 0 over dur seconds (0 outside)."""
    return math.sin(math.pi * x / dur) if x is not None and 0 <= x < dur else 0.0


# -- motion --------------------------------------------------------------------------------------------
def _angle(t, plan, cool=0.0):
    blows = plan[0]
    s, last, n, nxt = _beat(t, blows)
    rest = _HOVER + 56 * smoothstep(min(cool / 0.2, 1.0, (1 - cool) / 0.1))   # shouldered through the look-over
    for k in ("flip", "inspect"):                           # lifted clear for a flip or a close look
        if (u := _since(t, plan, k)) is not None:
            rest += 18 * smoothstep(min(u / 0.15, 1.0, (_LONG[k] - u) / 0.15))
    ping = last and _since(t, plan, "ping") == s
    recoil = _PING if ping else _RECOIL
    if last and s < recoil:                                 # bounce off the bar back up to the hover
        bounce = 34 if ping else 6 * last[1]                # a glancing blow kicks it way up
        rest = _REST + (_HOVER - _REST) * smoothstep(s / recoil) + bounce * math.sin(math.pi * s / recoil)
    if nxt is None:
        return rest
    top, lift, hold = _windup(nxt[1])
    if n < _SWING:                                          # smash: accelerates into the bar
        return top + (_REST - top) * (1 - n / _SWING) ** 2
    if n < _SWING + hold:                                   # hangs up top, a heavy one trembling
        return top + nxt[1] ** 3 * 1.2 * math.sin(t * 60)
    if n < _SWING + hold + lift:                            # lifting, straight out of any recoil
        return rest + (top - rest) * smoothstep(1 - (n - _SWING - hold) / lift)
    return rest


def _carry(f, a, b):
    """Swinging the bar from a to b, 0..1: an arc up and over."""
    e = smoothstep(f)
    return a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e - 10 * math.sin(math.pi * e)


def _bar_at(t, plan, cool):
    """(x, bottom y, heat 0..1, visible 0..1) of the workpiece: fetched from the fire (its light fading
    up as it comes), maybe sent back to reheat (dulling on the way there), cooling at the end, then
    set aside."""
    _, trip, _ = plan
    anvil = (_AX, _AY + 3)
    if t < _FETCH:
        return (*_carry(t / _FETCH, _FIRE, anvil), 1.0, smoothstep(t / 0.3))
    if trip:
        a, b = trip
        if t < a:                                           # dulling as it's worked -- time to reheat
            return (*anvil, 1 - 0.5 * smoothstep((t - _FETCH) / (a - _FETCH)), 1.0)
        if t < a + _TRIP:
            return (*_carry((t - a) / _TRIP, anvil, _FIRE), 0.5 + 0.2 * (t - a) / _TRIP, 1.0)
        if t < b - _TRIP:
            return (*_FIRE, 0.7 + 0.3 * smoothstep((t - a - _TRIP) / (b - a - 2 * _TRIP)), 1.0)
        if t < b:
            return (*_carry((t - b + _TRIP) / _TRIP, _FIRE, anvil), 1.0, 1.0)
    return (*anvil, 1 - cool, 1 - smoothstep((t - _PIECE + _ASIDE) / _ASIDE))


def _flipping(t, plan):
    """(hop px, how flat it looks 0..1) while the bar's being flipped over."""
    u = _since(t, plan, "flip")
    if u is None:
        return 0.0, 1.0
    f = u / _LONG["flip"]
    return 9 * math.sin(math.pi * f), abs(math.cos(math.pi * smoothstep(f)))


def _ember(u):
    """Where the big floating ember is, u s into its rise -- drifting up and swaying."""
    f = u / _LONG["ember"]
    return _AX + 4 + 9 * math.sin(f * 7) * f, _AY - 4 - 70 * f ** 1.3


def _jolt(t, plan):
    """(hit 0..1 fading after a blow, brace 0..1 building through a heavy wind-up)."""
    s, last, n, nxt = _beat(t, plan[0])
    hit = last[1] * (1 - s / 0.3) if last and s < 0.3 and last[1] > _TAP else 0.0
    brace = 0.0
    if nxt:
        _, lift, hold = _windup(nxt[1])
        if _SWING < n < _SWING + hold + lift:
            brace = nxt[1] * smoothstep(1 - (n - _SWING) / (hold + lift))
    return hit, brace


def _pose(now):   # eyes on the bar wherever it goes; widen on the wind-up, flinch on the hit
    t, plan, cool = _piece(now)
    hit, brace = _jolt(t, plan)
    bx, _, _, shown = _bar_at(t, plan, cool)
    over = math.sin(math.pi * cool)                         # the look-over swells in and out
    track = min(9.0, (bx - _AX) * 0.17) * shown             # follow the bar in (gently, as it appears)
    stray = _since(t, plan, "spark")
    flinch = _bump(stray - 0.28 if stray is not None else None, 0.45)
    ping = _bump(_since(t, plan, "ping"), 0.6)
    lean = _bump(_since(t, plan, "inspect"), _LONG["inspect"])
    hop, _ = _flipping(t, plan)
    gx = math.sin(now * 0.8) * 2 + over * 7 * math.sin(cool * math.tau * 1.5) + track - 3 * flinch
    gy = -5 + 2 * hit + over + 5 * lean - 0.25 * hop
    if (u := _since(t, plan, "ember")) is not None:         # watch the ember float up past
        ex, ey = _ember(u)
        k = _bump(u, _LONG["ember"]) ** 0.5
        gx, gy = gx + (ex - 64) * 0.12 * k, gy + max(-6.0, (ey - 34) * 0.15) * k
    h = 0.75 + 0.12 * brace - 0.3 * hit - 0.15 * over + 0.18 * ping - 0.45 * flinch - 0.3 * lean
    return gx, gy, h                                        # eyes up: the stage is below


# -- painting ------------------------------------------------------------------------------------------
class _Canvas:
    """Supersampled grey art plus its coverage mask -- what's a prop (gets a black rim) vs open air."""

    def __init__(self, W, H):
        self.art, self.mask = Image.new("L", (W * _SS, H * _SS)), Image.new("L", (W * _SS, H * _SS))
        self.a, self.m = ImageDraw.Draw(self.art), ImageDraw.Draw(self.mask)

    def poly(self, pts, grey, edge=None):
        xy = [(x * _SS, y * _SS) for x, y in pts]
        self.a.polygon(xy, fill=grey)
        self.m.polygon(xy, fill=255)
        if edge is not None:                                # a lit rim round a dark body
            self.a.line(xy + xy[:1], fill=edge, width=round(1.4 * _SS))

    def line(self, pts, grey, width):
        xy = [(x * _SS, y * _SS) for x, y in pts]
        self.a.line(xy, fill=grey, width=round(width * _SS))
        self.m.line(xy, fill=255, width=round(width * _SS))


def _anvil(c):
    """A dark anvil caught by the glow: lit face, dim body edged in light, curved horn, flared feet."""
    top = _AY + 4                                           # a dark hairline under the bar
    c.poly([(_AX - 13, top), (_AX - 25, top)] +
           [(_AX - 25 + 12 * f, top + 1.3 + 1.7 * f ** 1.5) for f in (i / 8 for i in range(9))], 255)  # horn
    c.poly([(_AX - 13, top), (_AX + 16, top), (_AX + 16, top + 3), (_AX - 13, top + 3)], 255)      # face
    c.poly([(_AX - 9, top + 3), (_AX + 10, top + 3), (_AX + 5, top + 7), (_AX + 14, 64),
            (_AX - 13, 64), (_AX - 4, top + 7)], 0, edge=255)                                      # body


def _bar(c, t, plan, cool):
    """The workpiece: stretches with every blow, flattens on a hit, hops and turns when flipped;
    white-hot, dimming as it cools. -> (left x, right x, top y, heat) for the light, steam and glint."""
    blows = plan[0]
    x, y, heat, shown = _bar_at(t, plan, cool)
    done = sum(1 for b in blows if b[0] <= t and b[1] > _TAP)
    s, last, _, _ = _beat(t, blows)
    squash = last[1] * (1 - s / 0.14) if last and s < 0.14 and last[1] > _TAP else 0.0
    hop, flat = _flipping(t, plan)
    half, th = 6 + 1.5 * done + 3 * squash, (3 - 1.2 * squash) * flat + 6 * (1 - flat)   # edge-on: taller, narrower
    half -= 2 * (1 - flat)
    y -= hop
    if shown > 0.05:
        c.poly([(x - half, y - th), (x + half, y - th), (x + half, y), (x - half, y)], round((105 + 150 * heat) * shown))
    return x - half, x + half, y - th, heat * shown


def _hammer(c, ang):
    """A cross-peen hammer in profile: a slim handle swelling toward the grip, its tip just poking
    through the head; a square head with a bevelled striking face, tapering to a wedge peen."""
    (hx, hy), (ux, uy), (px, py) = _hammer_at(ang)
    pt = lambda u, v: (hx + px * u + ux * v, hy + py * u + uy * v)
    L, T = _HEAD
    c.poly([pt(0.9, T + 1.2), pt(-0.9, T + 1.2), pt(-1.1, -16), pt(-1.8, -46),
            pt(1.8, -46), pt(1.1, -16)], 255)                                          # handle, through the head
    c.poly([pt(L, -T + 0.9), pt(L - 0.9, -T), pt(-1.5, -T), pt(-L + 0.6, -0.7), pt(-L, 0),
            pt(-L + 0.6, 0.7), pt(-1.5, T), pt(L - 0.9, T), pt(L, T - 0.9)], 255)      # head: face .. peen


def _swoosh(c, t, plan):
    """Speed lines trailing the head through a smash."""
    _, _, n, nxt = _beat(t, plan[0])
    if not nxt or n >= _SWING or nxt[1] < 0.5:
        return
    top, ang = _windup(nxt[1])[0], _angle(t, plan)
    for r in (_L - 2, _L + 6):
        c.line([(_GX + r * math.cos(math.radians(a)), _GY - r * math.sin(math.radians(a)))
                for a in (ang + (top - ang) * i / 6 * 0.7 for i in range(7))], 255, 1)


def _steam(g, t, plan, cool, bar, seed):
    """Steam off the cooling bar, summed into the haze: puffs leave the hot metal, rise ever faster
    as they warm the air, swell, sway and thin away -- stopping in time to clear before the next piece."""
    start = plan[0][-1][0] + 0.6
    t0, t1, rate = start + 0.1, _PIECE - _STEAM - 0.05, 14
    for n in range(max(0, math.ceil((t - _STEAM - t0) * rate)), math.floor((min(t, t1) - t0) * rate) + 1):
        born = t0 + n / rate
        a = t - born
        if a < 0 or a >= _STEAM:
            continue
        x0 = bar[0] + (bar[1] - bar[0]) * rand(seed, n, 1)
        heat = 1 - smoothstep((born - start) / (_PIECE - _ASIDE - start))   # less steam as it cools
        x = x0 + 4 * a * math.sin(3 * a + rand(seed, n, 2) * 6)
        y = bar[2] - 1 - 10 * a - 9 * a * a
        r = 1.5 + 6 * (1 - math.exp(-1.6 * a))
        soft_spot(g, x, y, r, r * 0.85, 0.5 * heat * smoothstep(a / 0.08) * (1 - a / _STEAM) ** 1.5, add=True)


def _glow(W, H, now, t, plan, cool, bar, flare, keep, seed):
    """The light and the haze: a halo round the hot bar (breathing, flaring on a blow) and the steam
    rising off it -- held back from the eyes and the props' rims."""
    g = Image.new("L", (W, H))
    heat = bar[3]
    breath = 2 * math.sin(now * 7) + math.sin(now * 17)
    r = (27 + 12 * flare + breath) * (0.4 + 0.6 * heat)
    soft_spot(g, (bar[0] + bar[1]) / 2, bar[2] + 2, r, 0.8 * r, (0.4 + 0.35 * flare) * heat)
    if cool:
        _steam(g, t, plan, cool, bar, seed)
    if (u := _since(t, plan, "ember")) is not None:         # the ember lights its own little halo
        ex, ey = _ember(u)
        soft_spot(g, ex, ey, 6, 6, 0.55 * (1 - smoothstep((u / _LONG["ember"] - 0.7) / 0.3)))
    return ImageChops.subtract(g, keep)


# -- effects drawn straight onto the frame -------------------------------------------------------------
def _sparks(d, s, blow):
    """A star flash, then a shower of streaking sparks arcing out and flickering out, and embers
    floating up. Drawn by flipping pixels, so they show over the eyes too."""
    p = blow[1]
    if s < 0.07:
        for deg in range(0, 360, 30):
            reach = 5 + s * 160 * p * (1.6 if deg % 90 == 0 else 1)
            c, sn = math.cos(math.radians(deg)), math.sin(math.radians(deg)) * 0.6
            for r in range(4, round(reach)):
                flip(d, _AX + c * r, _AY - 1 + sn * r)
    seed = int(blow[0] * 100)
    for i in range(6 + round(14 * p)):
        a = math.radians(10 + rand(seed, i, 1) * 160)
        spd = 45 + rand(seed, i, 2) * 110 * p
        vx, vy = math.cos(a) * spd, -math.sin(a) * spd
        x, y = _AX + vx * s, _AY + vy * s + 170 * s * s
        life = 0.6 - rand(seed, i, 3) * 0.25
        if y < 63 and s < life and (s < life - 0.12 or int(s * 40 + i) % 2):   # flicker as it dies
            flip(d, x, y)
            if s < 0.3:                                     # streaks while they're fast
                flip(d, x - vx * 0.015, y - (vy + 340 * s) * 0.015)
    for i in range(round(4 * p)):                           # embers drifting up, flickering out
        e = s - 0.1
        if 0 < e < 1.3 and int(e * 10 + i) % 4 and (e < 1.0 or int(e * 30) % 2):
            flip(d, _AX + (rand(seed, i, 9) - 0.5) * 18 + math.sin(e * 5 + i) * 2, _AY - 4 - e * 14)


def _ting(d, s, loud):
    """Ringing sound arcs off the anvil -- a tap's 'ting', or a glancing blow's sharp 'tink' -- the
    rings breaking into dashes as they fade."""
    end = 0.45 if loud else 0.3
    for k in range(2 if loud else 1):
        r = 4 + k * 4 + s * (40 if loud else 25)
        if s < end:
            dash = s > end * 0.6
            for side in (-1, 1):
                a0, a1 = (-35, 35) if side > 0 else (145, 215)
                step = 10 if dash else a1 - a0
                for a in range(a0, a1, step * 2 if dash else step):
                    d.arc([_AX + side * 4 - r, _AY - 2 - r * 0.7, _AX + side * 4 + r, _AY - 2 + r * 0.7],
                          a, min(a1, a + step), fill=1)


def _stray(d, s, ox, oy):
    """A spark that flies straight at Pip's left eye -- and fizzles out in a tiny star on arrival."""
    f = s / 0.28
    tx, ty = _EYE[0] + ox, _EYE[1] + oy
    if 0 <= f < 1:
        x, y = _AX + (tx - _AX) * f, _AY + (ty - _AY) * f - 8 * math.sin(math.pi * f)
        flip(d, x, y)
        flip(d, x + 1, y)
    elif f < 1.8:
        k = round(2 * (1.8 - f) / 0.8 + 0.4)                # the fizzle shrinks away
        for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
            flip(d, tx + 6 + dx, ty + 4 + dy)


def _flake(d, u, seed):
    """A flake of scale knocked off by a heavy blow: spinning off to one side and falling away."""
    side = 1 if rand(seed, 77) < 0.5 else -1
    x, y = _AX + side * (10 + 55 * u), _AY - 2 - 38 * u + 120 * u * u
    a = u * 25
    if y < 66:
        d.line([x - 2.5 * math.cos(a), y - 2.5 * math.sin(a), x + 2.5 * math.cos(a), y + 2.5 * math.sin(a)], fill=1, width=2)


def _float(d, u):
    """The big ember: a glowing mote drifting up, pulsing, winking out near the top."""
    x, y = _ember(u)
    f = u / _LONG["ember"]
    if f < 0.85 or int(u * 20) % 2:
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):    # a 2x2 mote...
            flip(d, x + dx, y + dy)
        if int(u * 5) % 2:                                  # ...pulsing brighter: a little cross
            for dx, dy in ((-1, 0), (2, 0), (0, -1), (1, 2)):
                flip(d, x + dx, y + dy)


def _glint(d, cool, bar):
    """A star of light running along the finished piece."""
    f = (cool - 0.55) / 0.3
    if 0 <= f < 1:
        x, y = bar[0] + (bar[1] - bar[0]) * smoothstep(f), bar[2] + 1
        for k in range(1, round(3 * math.sin(math.pi * f)) + 1):
            for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
                flip(d, x + dx, y + dy)
        flip(d, x, y)


def _sweat(d, cool, ox, oy):
    """A bead of sweat sliding down beside the right eye after a heavy piece, drying to nothing."""
    f = min(1.0, cool * 1.3)
    if 0.05 < f < 1:
        k = 1 - smoothstep((f - 0.55) / 0.45)               # shrinks away as it dries
        x, y = 108 + ox, 22 + oy + 12 * smoothstep(f)
        if k > 0.2:
            d.polygon([(x, y - 3 * k), (x - 2 * k, y + k), (x + 2 * k, y + k)], fill=1)
            d.ellipse([x - 2 * k, y - k, x + 2 * k, y + 2 * k], fill=1)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    img = frame(d)
    if img is None:
        return
    t, plan, cool = _piece(now)
    seed = int(rand(getattr(now, "seed", 0), getattr(now, "t", now) // _PIECE) * 1e6)
    blows = plan[0]
    s, last, _, _ = _beat(t, blows)
    c = _Canvas(W, H)
    _anvil(c)
    bar = _bar(c, t, plan, cool)
    _swoosh(c, t, plan)
    _hammer(c, _angle(t, plan, cool))
    art = c.art.resize((W, H), Image.BOX).point(lambda v: 255 if v >= 150 else v)   # crisp lines; greys stay grey
    cover = c.mask.resize((W, H), Image.BOX).point(lambda v: 255 if v >= 110 else 0)
    rim = cover.filter(ImageFilter.MaxFilter(3))
    keep = ImageChops.lighter(img.convert("L").filter(ImageFilter.MaxFilter(5)), rim)   # no light on the eyes / rims
    struck = last and last[1] > _TAP
    flare = last[1] * (1 - s / 0.25) if struck and s < 0.25 else 0.0
    grey = Image.composite(art, _glow(W, H, now, t, plan, cool, bar, flare, keep, seed), cover)
    img.paste(0, (0, 0), rim.convert("1"))                  # a black moat round the props
    img.paste(1, (0, 0), halftone(grey))
    if bar[3] > 0.65 and int(now * 12) % 2:                 # heat shimmer over the hot bar
        k = int(now * 12)
        flip(d, (bar[0] + bar[1]) / 2 + (rand(k) - 0.5) * 14, bar[2] - 2 - rand(k, 1) * 5)
    if struck and s < 1.4:
        _sparks(d, s, last)
    elif last and s < 0.3:
        _ting(d, s, False)
    for kind, draw in (("ping", lambda u: _ting(d, u, True)), ("spark", lambda u: _stray(d, u, ox, oy)),
                       ("scale", lambda u: _flake(d, u, seed)), ("ember", lambda u: _float(d, u))):
        if (u := _since(t, plan, kind)) is not None:
            draw(u)
    if cool:
        _glint(d, cool, bar)
        if max(b[1] for b in blows) >= 1.0:
            _sweat(d, cool, ox, oy)
    if struck and last[1] >= 0.8 and s < 0.12:            # a heavy blow shakes the screen
        amp = 3 * last[1] * (1 - s / 0.12)
        sx, sy = round(amp * math.sin(t * 90)), round(amp * math.cos(t * 70))
        if sx or sy:
            snap = img.copy()
            d.rectangle([0, 0, W - 1, H - 1], fill=0)
            img.paste(snap, (sx, sy))


ACTION = Action("working", mood="focused", pose=_pose, overlay=_overlay)


if __name__ == "__main__":
    kinds, moments = set(), set()
    for seed in range(600):
        plan = _plan(seed)
        blows, trip, events = plan
        kinds.add(len(blows))
        moments |= {k for k, _ in events}
        assert len({k for k, _ in events}) == len(events) <= 2, "up to two different moments a piece"
        for b in blows:
            assert abs(_angle(b[0], plan) - _REST) < 1, "every blow lands on the bar"
        for a, b in zip(blows, blows[1:]):
            _, lift, hold = _windup(b[1])
            assert b[0] - a[0] >= _SWING + lift + hold, "the wind-up fits between blows"
        _, lift, hold = _windup(blows[0][1])
        assert blows[0][0] - _SWING - lift - hold >= _FETCH, "the bar is on the anvil before the first swing"
        if trip:
            assert not any(trip[0] - 0.1 < b[0] < trip[1] + _SWING + 0.4 for b in blows), "no blows while it's away"
        assert blows[-1][0] + 0.6 + 1.2 <= _PIECE - _ASIDE, "time to look the bar over before it's set aside"
        for k, at in events:
            if k in ("flip", "inspect"):                    # a lull moment never overlaps a swing
                for i in range(int(_LONG[k] * 50)):
                    tt = at + i / 50
                    assert _HOVER - 1e-6 <= _angle(tt, plan) <= _HOVER + 18 + 1e-6, f"{k}: the hammer just waits, lifted clear"
            assert at + _LONG[k] <= _PIECE, f"{k} ends inside its piece"
    assert kinds == {2, 3, 4, 6, 7}, f"every rhythm should come up: {kinds}"
    assert moments == set(_LONG), f"every moment should come up: {moments}"
    for seed in range(50):                                  # the bar never jumps, and fades in from the fire
        plan = _plan(seed)
        pts = [_bar_at(i / 100, plan, 0.0)[:2] for i in range(int(_PIECE * 100) - 300)]
        assert max(math.dist(a, b) for a, b in zip(pts, pts[1:])) < 3, "the bar moves smoothly"
        assert _bar_at(0.0, plan, 0.0)[3] == 0, "its light fades up as it comes in"
    assert 55 < _AX < 72 and 46 < _AY < 52, f"the strike lands mid-screen, low: {_AX:.1f}, {_AY:.1f}"
    half = halftone(Image.new("L", (4, 4), 128))
    assert sum(bool(half.getpixel((x, y))) for x in range(4) for y in range(4)) == 8, "mid grey halftones to half"
    print("working ok")
