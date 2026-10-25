"""Thinking: formulas drift up past Pip's face while the squinting eyes gaze up and read the one
rising through the middle. Their tempo wanders between calm and busy, and every ~6.5s Pip draws a
random beat from a weighted deck (fresh per play):
  hmm        -- eyes narrow to slits and look off to a side, then ease open with an "oh"
  read       -- a formula types itself in mid-screen; the eyes lock on and squint tighter
  scribble   -- a formula types in, gets struck through, a skeptical double blink, it drops away
  merge      -- two formulas slide in from the edges and fuse into a new one (or a "?")
  lost       -- the formulas slow to a crawl, the eyes drift to a corner, one long slow blink
  racing     -- the formulas speed up and the eyes dart left-right after them
  eureka     -- a formula types in, a sparkle pops, the eyes open wide, it bursts into dots
Between beats the engine's own glances and blinks fire now and then. Where a formula passes over
an eye it flips to ink, so it never vanishes into the white. '^' raises the next char.

Self-check: `cd src && uv run python -m faces.actions.thinking`."""
import math

from PIL import Image, ImageChops, ImageDraw, ImageFont

from ..painters import sparkle
from ..primitives import frame, rand, smoothstep
from ..spec import Action

_FORMULAS = ("E=mc^2", "F=ma", "v=d/t", "i^2=-1", "dx/dt", "O(n^2)", "y=mx+b", "pV=nRT",
             "f'(x)", "n!", "x=-b/2a", "e^ix", "a^2+b^2")
_N, _RISE = 3, 4.5             # formulas on screen / s each takes to cross from bottom to top
_LANES = (6, 46, 86)           # left x of each lane (jittered per pass)
_SQUINT, _FOCUS = 0.55, 0.1    # eye height while reading / extra narrowing as a formula crosses the middle

_BEAT = 6.5                    # s per beat window
_DECK = (("hmm", 3), ("read", 3), ("scribble", 2), ("merge", 2), ("lost", 2), ("racing", 1), ("eureka", 1))
_DUR = {"hmm": 1.6, "read": 2.6, "scribble": 3.0, "merge": 3.0, "lost": 3.0, "racing": 1.8, "eureka": 2.6}
_TEMPO = {"lost": 0.15, "racing": 2.6}   # formula speed during these beats
_RAMP = 0.3                    # s a beat takes to ease in / out
_GLANCES = ("look_up", "blink_up", "double_blink")   # native gestures sprinkled between beats

try:
    _F, _SUP = ImageFont.load_default(size=10), ImageFont.load_default(size=8)
except TypeError:              # ancient Pillow
    _F = _SUP = ImageFont.load_default()


# -- the beat deck --------------------------------------------------------------------------------
def _clock(now):
    return getattr(now, "t", now), getattr(now, "seed", 0)


def _draw_beat(k, seed):
    """Window k's beat: a weighted draw from the deck, and where in the window it starts."""
    pick, total = rand(seed, k, 9) * sum(w for _, w in _DECK), 0
    for name, w in _DECK:
        total += w
        if pick < total:
            break
    return name, 0.8 + rand(seed, k, 8) * (_BEAT - _DUR[name] - 1.3)


def _beat(now):
    """(beat name, progress -- 0..1 while it runs, its envelope 0..1, window k, seed)."""
    t, seed = _clock(now)
    k, u = divmod(t, _BEAT)
    name, at = _draw_beat(k, seed)
    p, r = (u - at) / _DUR[name], _RAMP / _DUR[name]
    env = smoothstep(p / r) * smoothstep((1 - p) / r) if 0 <= p <= 1 else 0.0
    return name, p, env, k, seed


def _lane_time(now):
    """The formulas' own clock: a gentle tempo drift, slowed or sped through lost / racing beats."""
    t, seed = _clock(now)
    tau = t + 0.3 * (1 - math.cos(0.21 * t)) / 0.21              # speed 1 + 0.3 sin(0.21 t), integrated
    k, u = divmod(t, _BEAT)
    for j in range(int(k)):                                      # finished windows: closed form
        name, _ = _draw_beat(j, seed)
        tau += (_TEMPO.get(name, 1) - 1) * (_DUR[name] - _RAMP)
    name, at = _draw_beat(k, seed)
    if name in _TEMPO and u > at:                                # this window: integrate the envelope
        span = min(u, at + _DUR[name]) - at
        steps = max(1, int(span / 0.02))
        r = _RAMP / _DUR[name]
        for s in range(steps):
            p = (s + 0.5) * span / steps / _DUR[name]
            tau += (_TEMPO[name] - 1) * smoothstep(p / r) * smoothstep((1 - p) / r) * span / steps
    return tau


# -- formulas -------------------------------------------------------------------------------------
def _pass(i, now):
    """Lane i right now -> (text, x, y): rises from below the screen to off the top."""
    _, seed = _clock(now)
    k, u = divmod(_lane_time(now) / _RISE + i / _N, 1.0)       # staggered so one is always mid-rise
    text = "?" if rand(seed, i, k) < 0.1 else _FORMULAS[int(rand(seed, i, k, 2) * len(_FORMULAS))]
    x = _LANES[i] + rand(seed, i, k, 1) * 12 + math.sin(u * 5 + i * 2) * 3   # a gentle sway as it floats
    return text, x, 72 - u * 84


def _width(d, text):
    return sum(d.textlength(ch, font=_SUP if k and text[k - 1] == "^" else _F)
               for k, ch in enumerate(text) if ch != "^")


def _formula(d, x, y, text):
    """Draw a short formula; '^' raises the next char as a smaller superscript."""
    sup = False
    for ch in text:
        if ch == "^":
            sup = True
            continue
        font = _SUP if sup else _F
        d.text((x, y - 4 if sup else y), ch, font=font, fill=1)
        x += d.textlength(ch, font=font)
        sup = False


def _typed(text, q):
    """The first part of `text` typed so far (q 0..1)."""
    return text[: max(1, math.ceil(len(text) * min(1.0, q)))]


def _pick(seed, k, salt):
    return _FORMULAS[int(rand(seed, k, salt) * len(_FORMULAS))]


def _burst(d, cx, cy, q, n=10):
    """Dots flying out from (cx, cy) as q goes 0 -> 1."""
    for i in range(n):
        a, r = i * math.tau / n + 0.3, 3 + 26 * q
        x, y = cx + r * math.cos(a), cy + r * 0.6 * math.sin(a)
        d.rectangle([x, y, x + 1, y + 1], fill=1)


def _props(d, name, p, k, seed):
    """Whatever this beat draws on top of the rising formulas."""
    if not 0 <= p <= 1:
        return
    a = _pick(seed, k, 3)
    if name in ("read", "scribble", "eureka"):
        w = _width(d, a)
        x, y = 64 - w / 2, 26
        if name == "read":
            y -= 50 * smoothstep((p - 0.8) / 0.2)                  # done: it floats off upward
        if name == "scribble":
            y += 60 * max(0.0, (p - 0.7) / 0.3) ** 2                # rejected: it drops away
        if name == "eureka" and p > 0.72:                          # it bursts into dots
            _burst(d, 64, y + 6, (p - 0.72) / 0.28)
            return
        _formula(d, x, y, _typed(a, p / 0.25))
        if name == "scribble" and p > 0.35:                        # struck through
            d.line([x - 2, y + 6, x - 2 + (w + 4) * smoothstep((p - 0.35) / 0.2), y + 4], fill=1, width=2)
        if name == "eureka" and p > 0.33:                          # the idea sparkles
            sparkle(d, x + w + 4, y, 2 + 3 * smoothstep((p - 0.33) / 0.12))
    elif name == "merge":
        b = _pick(seed, k, 4)
        if p < 0.45:                                               # slide in from both edges
            q = smoothstep(p / 0.45)
            _formula(d, -40 + (64 - _width(d, a) - 2 + 40) * q, 26, a)
            _formula(d, 128 - (128 - 66) * q, 26, b)
        elif p < 0.55:
            _burst(d, 64, 31, (p - 0.45) / 0.1, 8)
        else:                                                      # fused: a new formula, or a "?"
            c = "?" if rand(seed, k, 5) < 0.35 else _pick(seed, k, 6)
            _formula(d, 64 - _width(d, c) / 2, 26 - 50 * smoothstep((p - 0.85) / 0.15), c)


# -- the eyes ---------------------------------------------------------------------------------------
def _blinks(p, lo, hi, n=1):
    """0..1 lid dip: `n` quick blinks spread through [lo, hi] of a beat."""
    return abs(math.sin(math.pi * n * (p - lo) / (hi - lo))) if lo <= p <= hi else 0.0


def _pose(now):   # read the middle formula; each beat steers the gaze and the squint
    t, _ = _clock(now)
    text, x, y = min((_pass(i, now) for i in range(_N)), key=lambda q: abs(q[2] - 24))
    gx, gy = (x + 12 - 64) * 0.18, -6 + math.sin(t * 0.4) * 1.5
    h = _SQUINT - _FOCUS * max(0.0, 1 - abs(y - 24) / 20)          # narrows a touch on the middle formula
    name, p, e, k, seed = _beat(now)
    side = -1 if rand(seed, k, 6) < 0.5 else 1
    to = lambda a, b: a + (b - a) * e                              # blend toward the beat's target
    if name == "hmm":
        gx, gy, h = to(gx, side * 12), gy - 3 * e, to(h, 0.3)
        w = (p - 0.85) * _DUR[name] / 0.6                          # the "oh": eyes ease open as it clicks
        h += 0.3 * math.sin(math.pi * w) if 0 < w < 1 else 0.0
    elif name == "read":
        gx, gy, h = to(gx, 0), to(gy, -2), to(h, 0.4)
    elif name == "scribble":
        gx, gy, h = to(gx, 0), to(gy, -2), to(h, 0.35 if 0.35 < p < 0.6 else 0.5)
        h *= 1 - 0.9 * _blinks(p, 0.6, 0.78, 2)                    # the skeptical double blink
    elif name == "merge":
        sweep = 9 * math.sin(p * math.pi * 3) if p < 0.45 else 0.0  # flick between the incoming pair
        gx, gy, h = to(gx, sweep), to(gy, -2), to(h, 0.8 if 0.45 < p < 0.7 else 0.5)
    elif name == "lost":
        gx, gy, h = to(gx, side * 14), to(gy, -8), to(h, 0.6)
        h *= 1 - 0.92 * _blinks(p, 0.45, 0.8)                      # one long slow blink
    elif name == "racing":
        gx, h = to(gx, 10 * (1 if math.sin(t * math.tau * 2.5) > 0 else -1)), to(h, 0.5)
    elif name == "eureka":
        wide = smoothstep((p - 0.33) / 0.1) * (1 - smoothstep((p - 0.8) / 0.15))
        gx, gy, h = to(gx, 0), to(gy, -2) - 4 * wide, h + (1.0 - h) * wide
    return gx, gy, h


def _glance(now):
    """Now and then, between beats, one of the engine's own glances or blinks."""
    t, seed = _clock(now)
    _, p, *_ = _beat(now)
    slot = int(t / 2.4)
    if 0 <= p <= 1.4 or rand(seed, slot, 11) > 0.35:
        return None
    return _GLANCES[int(rand(seed, slot, 12) * len(_GLANCES))]


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    img = frame(d)
    if img is None:
        return
    ink = Image.new("1", (W, H), 0)
    pen = ImageDraw.Draw(ink)
    name, p, _, k, seed = _beat(now)
    spotlight = name in ("read", "scribble", "merge", "eureka") and 0 <= p <= 1
    for i in range(_N):
        text, x, y = _pass(i, now)
        if not (spotlight and 8 < y < 44):                         # make room for the beat's own formula
            _formula(pen, x, y, text)
    _props(pen, name, p, k, seed)
    img.paste(ImageChops.logical_xor(img, ink))                    # over an eye the formula turns to ink


ACTION = Action("thinking", mood="neutral", pose=_pose, overlay=_overlay, tic=(_glance, 2.4))


if __name__ == "__main__":
    from ..spec import Now
    beats = {_beat(Now(0.0, k * _BEAT + _BEAT / 2, s))[0] for k in range(40) for s in range(4)}
    assert beats == {n for n, _ in _DECK}, f"every beat should come up: {beats}"
    assert not any(t.replace(".", "").isdigit() for t in _FORMULAS), "formulas only -- no bare numbers"
    taus = [_lane_time(Now(0.0, t / 10, 2)) for t in range(600)]
    assert all(b > a for a, b in zip(taus, taus[1:])), "the formulas never stop or run backwards"
    for t in range(900):                                           # a squint, never shut -- except a real blink
        now = Now(0.0, t / 10, 5)
        name, p, *_ = _beat(now)
        if not (name in ("scribble", "lost") and 0 <= p <= 1):
            assert 0.25 < _pose(now)[2] <= 1.0, (t, name, _pose(now)[2])
    print("thinking ok")
