"""Listening -- headphones on, into the music. Slim over-ears: a band arcs over Pip's head, a cup at each
side. Every song has its own tempo: the cups' grilles pulse on the beat; little notes
drift up and away; Pip's eyes bob to the beat and sway with the bar.

Each song has a moment or two:
  drop    the bass drops: a big thump, the whole face bounces, eyes squeezed shut in delight
  bliss   eyes drift half-closed, swaying slow -- lost in it
  pause   the music cuts out: no beat, no notes, Pip's eyes open wide and glance about -- then it's back
  adjust  the headband slips down a touch; Pip pushes it back up
  lean    someone's talking: Pip slips a cup off one ear and leans in, still and keen, nodding along
Songs fade out and in at the changeover, so the beat never stumbles.

Self-check: `cd src && uv run python -m faces.actions.listening`."""
import math
from functools import cache

from PIL import Image, ImageDraw, ImageFilter

from ..painters import lids
from ..primitives import flip, frame, rand, smoothstep
from ..spec import Action

_SONG = 9.0                    # s per song
_GAP = 0.5                     # s of quiet between songs
_EVENTS = (("drop", 1.6), ("bliss", 2.6), ("pause", 1.4), ("adjust", 1.2), ("lean", 2.6))   # (moment, s)
_SS = 4                        # supersample factor for the headphones
_CUP = (8, 20)                 # an ear cup's shell: width, height
_NOTES = (                     # little music notes, as pixel rows (x offsets of lit pixels)
    ((2,), (2,), (2,), (0, 1, 2), (0, 1)),                       # a quaver-ish crotchet
    ((1, 2, 3, 4), (1, 4), (1, 4), (0, 1, 3, 4), (0, 3)),        # two beamed quavers
)


# -- the plan ------------------------------------------------------------------------------------------
@cache
def _plan(s):
    """(tempo bpm, ((start s, moment, seconds), ...)) for one song -- one or two moments, apart."""
    bpm = 92 + rand(s, 1) * 44
    names = [e for e, _ in _EVENTS]
    out, t = [], 1.2 + rand(s, 2) * 1.0
    for i in range(1 + (rand(s, 3) < 0.55)):
        name = names[int(rand(s, 4, i) * len(names))]
        if any(name == o[1] for o in out):
            continue
        dur = dict(_EVENTS)[name]
        if t + dur > _SONG - _GAP - 0.4:
            break
        out.append((t, name, dur))
        t += dur + 1.0 + rand(s, 5, i) * 1.2
    return bpm, tuple(out)


def _song(now):
    """(seconds into this song, its tempo, its moments, the moment under way (name, u, dur) | None)."""
    T, seed = getattr(now, "t", now), getattr(now, "seed", 0)
    k, t = divmod(T, _SONG)
    bpm, events = _plan(int(rand(seed, k) * 1e6))
    cur = next(((n, t - a, d) for a, n, d in events if a <= t < a + d), None)
    return t, bpm, events, cur


def _ease(u, dur, edge=0.3):
    return smoothstep(min(u / edge, 1.0, (dur - u) / edge))


def _volume(t, cur):
    """0..1 how much music's playing: fading out and in at the song change, cut by a pause."""
    v = smoothstep(min(t / _GAP, 1.0, (_SONG - _GAP - t) / _GAP)) if t < _SONG - _GAP else 0.0
    if cur and cur[0] == "pause":
        v *= 1 - _ease(cur[1], cur[2], 0.15)
    return max(0.0, v)


def _beat(t, bpm):
    """(beats played, 0..1 how hard this beat's thump still rings)."""
    b = t * bpm / 60
    return b, math.exp(-(b % 1.0) * 6)


# -- drawing -------------------------------------------------------------------------------------------
def _headphones(img, W, H, thump, slip, lift):
    """Slim over-ears, drawn smooth: a band over the top, a slider down to each cup -- a rounded shell
    whose grille slot pulses on the beat, and a soft cushion against Pip. `lift` (0..1) eases the right
    cup off its ear."""
    S, (cw, ch) = _SS, _CUP
    lay = Image.new("L", (W * S, H * S))
    g = ImageDraw.Draw(lay)
    cy = H / 2 + 1 + slip                                   # the cups' middle
    top = cy - ch / 2
    off = 4 * lift
    for side in (-1, 1):
        x0 = 1.5 if side < 0 else W - 1.5 - cw + off        # the shell, outlined
        x1 = x0 + cw
        g.rounded_rectangle([x0 * S, top * S, x1 * S, (top + ch) * S], radius=4 * S, outline=255, width=S)
        cx = (x0 + x1) / 2
        r = 2.5 + 3 * thump                                 # the grille slot, pulsing on the beat
        g.rounded_rectangle([(cx - 0.6) * S, (cy - r) * S, (cx + 0.6) * S, (cy + r) * S], radius=S // 2, fill=255)
        c0 = x1 if side < 0 else x0 - 3                     # the cushion, a touch taller than the shell
        g.rounded_rectangle([c0 * S, (top - 1) * S, (c0 + 3) * S, (top + ch + 1) * S], radius=int(1.5 * S), fill=255)
        sx = cx - 1                                         # the slider, two rails up to the band
        g.rectangle([sx * S, (top - 5) * S, (sx + 2) * S, top * S], outline=255, width=S)
    band = [(cw / 2 + 1.5) * S, (1.5 + slip) * S, (W - cw / 2 - 1.5 + 2 * off) * S, (2 * (top - 5) - 1.5 + 2 * slip) * S]
    g.arc(band, 180, 360, fill=255, width=2 * S)            # the band
    small = lay.resize((W, H), Image.BOX).point(lambda v: 255 if v >= 110 else 0)
    img.paste(0, (0, 0), small.filter(ImageFilter.MaxFilter(3)).convert("1"))   # a black rim
    img.paste(1, (0, 0), small.convert("1"))


def _note(d, x, y, kind):
    for dy, row in enumerate(_NOTES[kind]):
        for dx in row:
            d.point((round(x) + dx, round(y) + dy), fill=1)


def _notes(d, W, H, t, vol, seed):
    """Little notes drifting up off the cups, under the band, swaying, winking out as they rise."""
    for i in range(4):
        f = (t * 0.35 + i / 4) % 1.0
        if vol * (1 - f) < 0.25 or f < 0.05:
            continue
        side = -1 if i % 2 else 1
        x = (13 if side < 0 else W - 19) - side * 2 * f + math.sin(t * 2 + i)
        y = 24 - 12 * f
        if f < 0.8 or int(t * 15) % 2:
            d.rectangle([round(x) - 1, round(y) - 1, round(x) + 5, round(y) + 5], fill=0)
            _note(d, x, y, int(rand(i, int(t * 0.35 + i / 4), seed % 97) * 2))


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    if frame(d) is None:
        return
    t, bpm, events, cur = _song(now)
    vol = _volume(t, cur)
    beats, ring = _beat(t, bpm)
    big = _ease(cur[1], cur[2], 0.2) if cur and cur[0] == "drop" else 0.0
    thump = ring * vol * (1 + 1.5 * big)
    slip = 0.0
    if cur and cur[0] == "adjust":                          # it slips down... and gets pushed back up
        u = cur[1]
        slip = 3 * smoothstep(u / 0.35) * (1 - smoothstep((u - 0.7) / 0.35))
    lift = _ease(cur[1], cur[2], 0.4) if cur and cur[0] == "lean" else 0.0
    _headphones(frame(d), W, H, thump, slip, lift)
    _notes(d, W, H, t, vol, int(rand(getattr(now, "seed", 0), 3) * 1e6))
    if big and ring > 0.6:                                  # the drop: the screen thumps with it
        img = frame(d)
        snap = img.copy()
        d.rectangle([0, 0, W - 1, H - 1], fill=0)
        img.paste(snap, (0, 1 if int(t * 40) % 2 else -1))


def _shut(now):
    """0..1 how closed Pip's eyes are: squeezed on the drop, drifting half-shut in bliss."""
    t, bpm, events, cur = _song(now)
    if not cur:
        return 0.0
    name, u, dur = cur
    if name == "drop":
        return 0.7 * _ease(u, dur, 0.15)
    if name == "bliss":
        return 0.5 * _ease(u, dur, 0.5)
    return 0.0


def _eyes(d, x, y, w, h, right, now):
    """Pip's eyes, closing in delight on a drop or half-shut in bliss; plain otherwise."""
    k = _shut(now)
    if k > 0.02:
        lids(d, x, y, w, h, top=0.5 * k, bottom=1 - 0.3 * k)


def _pose(now):   # bob to the beat, sway with the bar; still and keen when someone's talking
    t, bpm, events, cur = _song(now)
    vol = _volume(t, cur)
    beats, ring = _beat(t, bpm)
    sway = math.sin(math.pi * beats / 2) * 2.5 * vol        # a lean every other beat
    gx, gy, h = sway, -1.5 * ring * vol + 1, 1.0
    if cur:
        name, u, dur = cur
        k = _ease(u, dur)
        if name == "bliss":                                 # slow and dreamy
            gx = gx * (1 - k) + math.sin(t * 1.6) * 3 * k
        elif name == "pause":                               # it stopped? wide eyes glancing about
            gx, h = gx * (1 - k) + math.sin(u * 5) * 4 * k, h + 0.12 * k
        elif name == "adjust":
            gy -= 1.5 * math.sin(math.pi * u / dur)
        elif name == "lean":                                # still, keen, toward the bare ear, nodding along
            gx, gy = gx * (1 - k) + 4 * k, gy * (1 - k) + 2 * math.sin(u * 5) * k
            h -= 0.08 * k
        elif name == "drop":
            gy += 2 * ring * k
    return gx, gy, h


ACTION = Action("listening", mood="attentive", pose=_pose, overlay=_overlay, eyes=_eyes)


if __name__ == "__main__":
    seen = set()
    for s in range(300):
        bpm, events = _plan(s)
        seen |= {n for _, n, _ in events}
        assert 92 <= bpm <= 136, "a sensible tempo"
        assert events and events[-1][0] + events[-1][2] <= _SONG - _GAP - 0.4, "moments end before the fade"
        assert all(a[0] + a[2] < b[0] for a, b in zip(events, events[1:])), "one moment at a time"
    assert seen == {n for n, _ in _EVENTS}, seen
    assert _volume(0.0, None) == 0 and _volume(_SONG - 0.01, None) == 0, "songs fade in and out: no stumble"
    vols = [_volume(i / 30, None) for i in range(int(_SONG * 30))]
    assert max(abs(b - a) for a, b in zip(vols, vols[1:])) < 0.1, "the volume eases"
    print("listening ok")
