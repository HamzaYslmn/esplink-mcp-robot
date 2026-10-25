"""Pip's eyes become slot reels: pull the arm, spin ~3s, a match rains coins -- "jackpot".

Self-ending action. The engine still draws the eyes; the overlay cuts dark symbols into them
(black-on-black off-eye is invisible, so each eye is its own reel window). Each eye is a little
spinning drum -- symbols sit at equal angles around it and foreshorten as they roll over the
edge, so only one is full-size at a time. ALWAYS_WIN forces a match every spin, for testing."""
import bisect
import math

from PIL import Image, ImageDraw, ImageFont

from ..primitives import frame, rand
from ..painters import sparkle
from ..spec import Vibe

ALWAYS_WIN = False              # True = force a match every spin (testing)

# timeline, seconds since the pull
_SPIN_START = 0.22              # arm bottoms out -> reels start
_STOP_L, _STOP_R = 2.7, 3.2     # eyes stop one at a time (~3s spin)
_RESULT = _STOP_R               # both home -> read the win
_SPAWN_DUR = 1.0                # coins keep launching this long after a win
_COIN_LIFE = 2.6                # a coin's airtime
_END_WIN = _RESULT + 3.0        # rain the coins, then self-end
_END_LOSE = _RESULT + 0.9       # near miss -> short beat, then self-end

_STRIP = "3$A5#9K2@8B4*6%J1&Z"  # the reel tape (no 7 -> only the win lands one)
_WIN_CHAR = "7"
_WIN_ODDS = 0.20                # chance a spin lands a match
_FINAL_K = (33, 38)             # glyphs each reel scrolls before stopping
_SLIDE = 0.07                   # slip time between detents; the rest of a step is a held pause
_SETTLE = 0.35                  # post-stop rock-and-settle
_DRUM_R = 17.0                  # drum radius (px) -> a symbol vanishes ~the eye edge
_DRUM_DPHI = math.radians(140)  # angle between symbols -> ~one in view at a time

_EYE_W, _EYE_H, _GAP = 36, 36, 10   # EyeEngine defaults -> reel centres
_PX, _PY, _L, _KN = 111, 45, 13, 4  # lever pivot, arm length, knob radius
_G, _FLOOR = 230.0, 62          # coin gravity (px/s^2), bounce floor
_N_COINS, _SPIN_SPD = 20, 9.0   # coins per burst, flip rate (rad/s)

try:
    _FONT = ImageFont.load_default(size=28)
except TypeError:               # ancient Pillow
    _FONT = ImageFont.load_default()


def _glyph_img(ch):             # one white-on-black glyph bitmap, trimmed to its ink
    bb = ImageDraw.Draw(Image.new("1", (1, 1))).textbbox((0, 0), ch, font=_FONT)
    g = Image.new("1", (max(1, bb[2] - bb[0]), max(1, bb[3] - bb[1])), 0)
    ImageDraw.Draw(g).text((-bb[0], -bb[1]), ch, font=_FONT, fill=1)
    return g


_GLYPHS = {c: _glyph_img(c) for c in dict.fromkeys(_STRIP + _WIN_CHAR)}

_state = {"start": None, "last": -1.0}   # a >0.5s gap means a fresh run


def _elapsed(now):
    """Seconds since this run began (a gap restarts the clock)."""
    s = _state
    if s["start"] is None or now - s["last"] > 0.5 or now < s["last"]:
        s["start"] = now
    s["last"] = now
    return now - s["start"]


def _won(seed):                 # a fresh spin wins with _WIN_ODDS odds
    return ALWAYS_WIN or rand(seed, 0, 1) < _WIN_ODDS


def _final_char(reel, seed):    # where an eye settles: matched 7s on a win, else two clear misses
    if _won(seed):
        return _WIN_CHAR
    n = len(_STRIP)
    i = int(rand(seed, 0, 9) * n)
    if reel == 1:               # force the right eye to a different symbol -> never a fake match
        i = (i + 1 + int(rand(seed, 1, 9) * (n - 1))) % n
    return _STRIP[i]


def _ticks(N, span):            # detent times under constant deceleration (fast early, slow late)
    v0, a = 2 * N / span, 2 * N / (span * span)
    return [(v0 - math.sqrt(max(0.0, v0 * v0 - 2 * a * k))) / a for k in range(N + 1)]


_SPAN = (_STOP_L - _SPIN_START, _STOP_R - _SPIN_START)
_TICKS = (_ticks(_FINAL_K[0], _SPAN[0]), _ticks(_FINAL_K[1], _SPAN[1]))


def _click(x):                  # a slip that overshoots the detent a touch, then settles -- a clunk
    x -= 1
    return 1 + 2.7 * x ** 3 + 1.7 * x ** 2


def _reel_pos(reel, t):
    """Reel position in symbols: slips detent->detent then HOLDS -> a real reel's stutter."""
    tau = t - _SPIN_START
    if tau <= 0:
        return 0.0
    ticks, N = _TICKS[reel], _FINAL_K[reel]
    if tau >= ticks[-1]:                                 # stopped -> a damped rock into place
        dt = tau - ticks[-1]
        if dt >= _SETTLE:
            return float(N)
        return N + math.sin(dt / _SETTLE * 2 * math.pi) * 0.18 * (1 - dt / _SETTLE)
    k = bisect.bisect_right(ticks, tau) - 1
    local, dur = tau - ticks[k], ticks[k + 1] - ticks[k]
    slide = min(_SLIDE, dur)
    return float(k + 1) if local >= slide else k + _click(local / slide)   # slip, then hold


def _glyph_at(reel, k, seed):   # cell k's glyph; the landing cell is the result
    if k >= _FINAL_K[reel]:
        return _final_char(reel, seed)
    return _STRIP[int(rand(reel * 211 + k, 5, 2) * len(_STRIP))]


def _cut_glyph(img, cx, cy, ch, sy):    # cut one drum symbol (squashed by sy) into the lit eye
    g = _GLYPHS[ch]
    h = max(1, round(g.height * sy))
    if h != g.height:
        g = g.resize((g.width, h), Image.NEAREST)
    img.paste(0, (round(cx - g.width / 2), round(cy - h / 2)), g)


def _reel_symbols(img, cx, cy, reel, t, seed):
    """Each eye is a spinning drum: symbols at equal angles, foreshortened over the curve, so
    only the front one is full-size -- the rest roll off the edge as thin slivers."""
    pos = _reel_pos(reel, t)
    k0 = round(pos)
    for n in (k0 - 1, k0, k0 + 1):
        ang = (pos - n) * _DRUM_DPHI                     # 0 = dead front; +/-90deg = the rim
        depth = math.cos(ang)
        if depth <= 0.05:                                # rolled past the rim / onto the back
            continue
        _cut_glyph(img, cx, cy - _DRUM_R * math.sin(ang), _glyph_at(reel, n, seed), depth)


def _arm_angle(t):              # lever angle: rests up, yanks down, springs back
    up, down = -1.45, 0.2
    if t < 0.05:
        return up
    if t < 0.20:                                         # yank down
        return up + (down - up) * ((t - 0.05) / 0.15) ** 2
    if t < 0.24:                                         # bottom -> trigger
        return down
    if t < 0.55:                                         # spring back with overshoot
        u = (t - 0.24) / 0.31
        return down + (up - down) * (u * u * (3 - 2 * u)) - math.sin(u * math.pi) * 0.12 * (1 - u)
    return up


def _draw_lever(d, t):
    th = _arm_angle(t)
    kx, ky = _PX + _L * math.cos(th), _PY + _L * math.sin(th)
    d.line([_PX, _PY, kx, ky], fill=1, width=3)                          # rod
    d.ellipse([_PX - 3, _PY - 3, _PX + 3, _PY + 3], fill=1)              # mount
    d.ellipse([kx - _KN, ky - _KN, kx + _KN, ky + _KN], fill=1)          # knob
    d.ellipse([kx - _KN + 1, ky - _KN + 1, kx + _KN - 2, ky + _KN - 2], fill=0)   # shine
    d.ellipse([kx - 1, ky - 1, kx + 1, ky + 1], fill=1)                  # centre


def _coin_pos(seed, c, a):      # ballistic coin at age `a`, with one floor bounce
    ox = 64 + (rand(seed, c, 4) * 2 - 1) * 18
    vx = (rand(seed, c, 2) * 2 - 1) * 70
    vy, oy = -55 - rand(seed, c, 3) * 85, 28.0
    af = (-vy + math.sqrt(vy * vy + 2 * _G * (_FLOOR - oy))) / _G        # time to the floor
    if a <= af:
        return ox + vx * a, oy + vy * a + 0.5 * _G * a * a
    a2, vx2 = a - af, vx * 0.7                                           # after the bounce
    return ox + vx * af + vx2 * a2, _FLOOR + (-(vy + _G * af) * 0.5) * a2 + 0.5 * _G * a2 * a2


def _draw_coins(d, W, H, ct, seed):
    """Gold coins scatter from the win, each flipping edge-to-face as it flies."""
    for c in range(_N_COINS):
        a = ct - (c / _N_COINS) * _SPAWN_DUR
        if a < 0 or a > _COIN_LIFE:
            continue
        x, y = _coin_pos(seed, c, a)
        if y > H + 6 or x < -6 or x > W + 6:
            continue
        r = 4 if rand(seed, c, 6) > 0.5 else 3
        face = abs(math.cos(a * _SPIN_SPD + c * 1.3))                    # 0 edge-on .. 1 face-on
        rw = max(0.18, face) * r
        d.ellipse([x - rw, y - r, x + rw, y + r], fill=1)
        if face > 0.55:                                                 # face-on -> emboss + glint
            d.ellipse([x - rw * 0.5, y - r * 0.5, x + rw * 0.5, y + r * 0.5], fill=0)
            d.point((x - rw * 0.3, y - r * 0.4), fill=1)
        if face > 0.85 and rand(seed, c, 7) > 0.55:
            sparkle(d, x, y, 2)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    t = _elapsed(now)
    seed = _state["start"] or now
    img = frame(d)
    lx = (W - (2 * _EYE_W + _GAP)) // 2                  # left-eye slot origin
    cy = (H - _EYE_H) // 2 + _EYE_H / 2 + oy             # eye centre (rides the gaze)
    if img is not None:
        _reel_symbols(img, lx + _EYE_W / 2 + ox, cy, 0, t, seed)
        _reel_symbols(img, lx + _EYE_W * 1.5 + _GAP + ox, cy, 1, t, seed)
    _draw_lever(d, t)
    if _won(seed) and t >= _RESULT:
        _draw_coins(d, W, H, t - _RESULT, seed)


def _expired(now, start):       # self-end after the coins rain (win) or a short miss
    t = _elapsed(now)
    return t >= (_END_WIN if _won(_state["start"]) else _END_LOSE)


VIBE = Vibe("jackpot", mood="neutral", overlay=_overlay, expired=_expired, still=True)
