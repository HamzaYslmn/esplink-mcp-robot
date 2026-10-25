"""Editing -- Pip at the keyboard, writing. Two chibi hands work a little keyboard along the bottom; the
line being written runs along the top, word by word (each word a bar of character cells), a caret
riding its end -- solid while typing, blinking while Pip stops to think. Pip's eyes follow the
caret along the line.

It writes the way people do, a fresh script each stretch:
  type     words go down in bursts, each key dipping under a fingertip, the thumb hitting space
  think    the hands rest, the caret blinks, Pip's eyes drift up and away
  delete   backspace hammered: the last word eaten char by char
  typo     a word goes in wrong -- a squiggle under it, Pip squints, backspaces, retypes
  cut      the last word or two highlighted, then gone
  save     ctrl+S: both hands down, a tick pops at the caret, Pip gives a little nod
  enter    the line's done: it scrolls up and away, the caret drops to a fresh line
Every stretch ends saved, on an empty line -- so one runs into the next with no jump.

Self-check: `cd src && uv run python -m faces.actions.editing`."""
import math
from functools import cache

from PIL import Image, ImageDraw, ImageFilter

from ..primitives import frame, rand, smoothstep
from ..spec import Action

_STRETCH = 12.0                # s per script (then a fresh one)
_CPS = 9.0                     # characters a second, typing
_CELL = 4                      # px per character: a 3x5 rune and a 1 px gap
_LINE = (4, 2)                 # where the line starts: x, top y
_RUNES = (                     # Elder-Futhark-ish runes as 1 px strokes on a 3x5 grid: (x0, y0, x1, y1)
    ((0, 0, 0, 4), (0, 2, 2, 0), (0, 3, 2, 1)),                      # fehu
    ((0, 0, 0, 4), (0, 0, 2, 1), (2, 1, 2, 4)),                      # uruz
    ((0, 0, 0, 4), (0, 1, 2, 2), (2, 2, 0, 3)),                      # thurisaz
    ((0, 0, 0, 4), (0, 0, 2, 1), (0, 2, 2, 3)),                      # ansuz
    ((0, 0, 0, 4), (0, 0, 2, 1), (2, 1, 0, 2), (0, 2, 2, 4)),        # raido
    ((2, 0, 0, 2), (0, 2, 2, 4)),                                    # kaunan
    ((0, 0, 2, 4), (2, 0, 0, 4)),                                    # gebo
    ((0, 0, 0, 4), (0, 0, 2, 1), (2, 1, 0, 2)),                      # wunjo
    ((0, 0, 0, 4), (2, 0, 2, 4), (0, 1, 2, 3)),                      # haglaz
    ((1, 0, 1, 4), (0, 1, 2, 3)),                                    # naudiz
    ((1, 0, 1, 4),),                                                 # isaz
    ((1, 0, 1, 4), (1, 2, 0, 0), (1, 2, 2, 0)),                      # algiz
    ((2, 0, 0, 2), (0, 2, 2, 2), (2, 2, 0, 4)),                      # sowilo
    ((1, 0, 1, 4), (1, 0, 0, 1), (1, 0, 2, 1)),                      # tiwaz
    ((0, 0, 0, 4), (2, 0, 2, 4), (0, 0, 1, 1), (1, 1, 2, 0)),        # ehwaz
    ((0, 0, 0, 4), (0, 0, 2, 1)),                                    # laguz
    ((1, 0, 2, 2), (2, 2, 1, 4), (1, 4, 0, 2), (0, 2, 1, 0)),        # ingwaz
)
_MAX_X = 116                   # a line this long gets an enter
_ROWS = (54, 59)               # top y of the keyboard's two rows of keycaps
_KEYS = [17 + 8 * i for i in range(12)]   # left x of each keycap (6 px wide, 2 px apart)
_SPACE = (41, 86)              # the spacebar, in the bottom row
_BACK, _ENTER, _CTRL, _S = (105, 0), (105, 1), (17, 1), (33, 0)   # (key x, row)
_HOME = (36, 92)               # x of the left / right hand at rest
_SCROLL = 0.3                  # s an enter's scroll takes


# -- the script ----------------------------------------------------------------------------------------
@cache
def _script(s):
    """The stretch as a list of events (time s, kind, arg), in time order:
    ('key', ((key x, row), rune)) appends a rune (index * 2 + mirrored, from 1); ('space', None); ('bs', None) deletes the last char;
    ('typo', n) underlines the last n chars; ('sel', n) highlights them, ('cut', n) removes them;
    ('think', seconds); ('save', None); ('enter', None); ('indent', n) opens a line n cells in."""
    indent = lambda i: (0, 1, 2, 1)[int(rand(s, i, 30) * 4)] * _CELL   # code: lines nest
    x0 = _LINE[0] + indent(0)
    ev, t, x, i, fresh = [(0.3, "indent", (x0 - _LINE[0]) // _CELL)], 0.6, x0, 0, True
    end = _STRETCH - 3.6                                    # the longest step (a typo) still leaves room to save + enter

    def word(n, at):
        for k in range(n):
            key = (_KEYS[1 + int(rand(s, i, k, 1) * 10)], int(rand(s, i, k, 2) * 2))
            rune = 1 + int(rand(s, i, k, 4) * len(_RUNES)) * 2 + (rand(s, i, k, 5) < 0.3)   # some mirrored
            ev.append((at + k / _CPS * (0.8 + 0.4 * rand(s, i, k, 3)), "key", (key, rune)))
        return at + n / _CPS

    while t < end:
        i += 1
        r, n = rand(s, i, 0), 2 + int(rand(s, i, 9) * 4)
        if x + (n + 1) * _CELL > _MAX_X:                    # line's full: done with it
            ev.append((t, "enter", None))
            x0 = _LINE[0] + indent(i)
            ev.append((t + _SCROLL, "indent", (x0 - _LINE[0]) // _CELL))
            t, x, fresh = t + _SCROLL + 0.25, x0, True
        elif r < 0.55 or fresh:                             # a word and a space
            t = word(n, t)
            ev.append((t, "space", None))
            t, x, fresh = t + 1 / _CPS + 0.05 * rand(s, i, 4), x + (n + 1) * _CELL, False
        elif r < 0.67:                                      # stop and think
            d = 0.7 + rand(s, i, 5) * 0.9
            ev.append((t, "think", d))
            t += d
        elif r < 0.76 and x > x0 + 5 * _CELL:               # backspace the last word away
            m = min(n, (x - x0) // _CELL - 1)
            for k in range(m):
                ev.append((t + k * 0.07, "bs", None))
            t, x = t + m * 0.07 + 0.15, x - m * _CELL
        elif r < 0.86:                                      # a typo: spotted, fixed
            t = word(n, t)
            ev.append((t + 0.1, "typo", n))
            for k in range(n):
                ev.append((t + 0.7 + k * 0.06, "bs", None))
            t = word(n, t + 0.75 + n * 0.06)
            ev.append((t, "space", None))
            t, x = t + 1 / _CPS + 0.1, x + (n + 1) * _CELL
        elif x > x0 + 6 * _CELL:                           # select the last word or so, cut it
            m = min((x - x0) // _CELL - 1, n + 1)
            ev.append((t, "sel", m))
            ev.append((t + 0.45, "cut", m))
            t, x = t + 0.7, x - m * _CELL
        else:                                               # save as you go
            ev.append((t, "save", None))
            t += 0.6
    ev.append((t + 0.1, "save", None))                      # end saved, on an empty line
    ev.append((t + 0.65, "enter", None))
    return tuple(sorted(ev, key=lambda e: e[0]))


def _seed(now):
    T, seed = getattr(now, "t", now), getattr(now, "seed", 0)
    return int(rand(seed, T // _STRETCH) * 1e6)


def _state(now):
    """Replay the script to now -> a dict: chars (a rune code, 0 = space), the scrolling-off line, marks
    (typo/select spans), the last event, the key under way, thinking, saved-tick and scroll timers."""
    t, ev = getattr(now, "t", now) % _STRETCH, _script(_seed(now))
    st = {"t": t, "chars": [], "old": None, "typo": 0, "sel": 0, "key": None, "think": None,
          "save": None, "enter": None, "last": None}
    for at, kind, arg in ev:
        if at > t:
            break
        st["last"] = (at, kind)
        if kind == "key":
            st["chars"].append(arg[1])
            st["key"] = (at, arg[0])
        elif kind == "space":
            st["chars"].append(0)
            st["key"] = (at, "space")
        elif kind == "bs":
            st["chars"] = st["chars"][:-1]
            st["key"] = (at, _BACK)
            st["typo"] = 0                                  # fixing it: the squiggle goes
        elif kind == "typo":
            st["typo"] = arg
        elif kind == "sel":
            st["sel"], st["seltime"] = arg, at
        elif kind == "cut":
            st["chars"], st["sel"] = st["chars"][:-arg], 0
            st["key"] = (at, _BACK)
        elif kind == "think":
            st["think"] = (at, arg)
        elif kind == "save":
            st["save"], st["savex"] = at, _caret_x(st["chars"])
            st["key"] = (at, "save")
        elif kind == "enter":
            st["old"], st["chars"], st["enter"], st["typo"] = st["chars"], [], at, 0
            st["key"] = (at, _ENTER)
        elif kind == "indent":
            st["chars"] = [0] * arg
    return st


# -- drawing -------------------------------------------------------------------------------------------
def _caret_x(chars):
    return _LINE[0] + len(chars) * _CELL


def _rune(d, x, y, code, ink=1):
    """Draw rune `code` (index * 2 + mirrored, from 1) with its top-left at (x, y)."""
    idx, mirror = divmod(code - 1, 2)
    for x0, y0, x1, y1 in _RUNES[idx]:
        if mirror:
            x0, x1 = 2 - x0, 2 - x1
        d.line([x + x0, y + y0, x + x1, y + y1], fill=ink)


def _line(d, chars, y, typo=0, sel=0, gone=0.0):
    """One line of runes; a selection inverted, a typo squiggled under. Scrolling off, it rises and
    crumbles rune by rune."""
    x0, top = _LINE[0], y
    if gone:
        top -= 9 * smoothstep(gone)
    n = len(chars)
    if sel:                                                 # highlighted: a lit band, the runes cut out of it
        d.rectangle([x0 + (n - sel) * _CELL - 1, top - 1, x0 + n * _CELL - 1, top + 5], fill=1)
    for k, c in enumerate(chars):
        if c and (not gone or rand(k, 3) > gone * 1.3):
            _rune(d, x0 + k * _CELL, top, c, 0 if sel and k >= n - sel else 1)
    if typo:                                                # a squiggle under the bad word
        for x in range(x0 + (n - typo) * _CELL, x0 + n * _CELL - 1):
            d.point((x, top + 6 + (x // 2) % 2), fill=1)


def _hand(d, cx, cy, left, finger):
    """A chibi hand from above-front: a rounded back, four separate fingers (one dipping to press),
    a thumb tucked in toward the middle."""
    thumb = cx + (7 if left else -7)
    d.rounded_rectangle([thumb - 2, cy - 2, thumb + 2, cy + 3], radius=2, fill=1)
    d.rounded_rectangle([cx - 7, cy - 6, cx + 7, cy], radius=3, fill=1)
    for k in range(4):
        fx = cx - 6 + k * 4 + (1 if left else -1) * 0
        dip = 2 if k == finger else 0
        d.rounded_rectangle([fx - 1, cy - 2 + dip, fx + 1, cy + 3 + dip], radius=1, fill=1)
        if k < 3:
            d.line([fx + 2, cy - 1, fx + 2, cy + 3 + dip], fill=0)   # the gap between fingers


def _keyboard(d, pressed):
    """A keyboard slab: a rounded body, two rows of slim keycaps and a spacebar; a pressed key sinks."""
    d.rounded_rectangle([13, 51, 114, 66], radius=3, outline=1)
    caps = [((x, row), x, x + 5) for row in range(2) for x in _KEYS if not (row and _SPACE[0] <= x < _SPACE[1])]
    for key, a, b in caps + [("space", _SPACE[0], _SPACE[1])]:
        y = _ROWS[1 if key == "space" else key[1]]
        if key in pressed:
            d.line([a, y + 2, b, y + 2], fill=1)            # pressed: sunk to a sliver
        else:
            d.rectangle([a, y, b, y + 1], fill=1)


def _press(st):
    """(keys down now, left hand x, right hand x, pressing finger left, right) from the key under way."""
    t, key = st["t"], st["key"]
    pressed, lx, rx, lf, rf = set(), _HOME[0], _HOME[1], -1, -1
    if key and t - key[0] < 0.11:
        k = key[1]
        if k == "space":
            pressed.add("space")
        elif k == "save":
            pressed |= {_CTRL, _S}
            lx, lf = _HOME[0] - 4, 1
        else:
            pressed.add(k)
            if k[0] + 3 < 64:
                lx, lf = _HOME[0] + (k[0] + 3 - _HOME[0]) * 0.45, min(3, max(0, int((k[0] + 3 - lx + 8) / 4)))
            else:
                rx, rf = _HOME[1] + (k[0] + 3 - _HOME[1]) * 0.45, min(3, max(0, int((k[0] + 3 - rx + 8) / 4)))
    return pressed, lx, rx, lf, rf


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    if frame(d) is None:
        return
    st = _state(now)
    t, chars = st["t"], st["chars"]
    if st["old"] is not None and t - st["enter"] < _SCROLL:    # the finished line scrolling off
        _line(d, st["old"], _LINE[1], gone=(t - st["enter"]) / _SCROLL)
    drop = 1 - smoothstep((t - st["enter"]) / _SCROLL) if st["enter"] is not None else 0.0
    y = _LINE[1] + round(6 * drop)                          # the fresh line slides up into place
    _line(d, chars, y, st["typo"], st["sel"])
    cx = _caret_x(chars)
    typing = st["last"] and st["last"][1] in ("key", "space", "bs") and t - st["last"][0] < 0.4
    if typing or int(t * 2.2) % 2 == 0:                     # solid while typing, blinking at rest
        d.line([cx, y - 1, cx, y + 5], fill=1)
    if st["save"] is not None and t - st["save"] < 0.7:     # the saved tick pops up and fades
        u = (t - st["save"]) / 0.7
        bx, by = min(st["savex"] + 5, 120), _LINE[1] + 3 - 3 * smoothstep(u * 2)
        if u < 0.75 or int(u * 20) % 2:
            d.line([bx, by, bx + 2, by + 2, bx + 6, by - 3], fill=1)
    pressed, lx, rx, lf, rf = _press(st)
    _keyboard(d, pressed)
    rest = 0 if st["think"] is None or t > sum(st["think"]) else 1   # resting hands lift a touch
    img = frame(d)
    lay = Image.new("1", (W, H))                            # hands on their own layer: rimmed in black
    g = ImageDraw.Draw(lay)
    for hx, left, f in ((lx, True, lf), (rx, False, rf)):
        _hand(g, hx, 51 - rest + (1 if f >= 0 else 0), left, f)
    img.paste(0, (0, 0), lay.convert("L").filter(ImageFilter.MaxFilter(3)).convert("1"))
    img.paste(1, (0, 0), lay)


def _pose(now):   # eyes follow the caret; drift up and away thinking; squint at a typo; nod on a save
    st = _state(now)
    t = st["t"]
    gx, gy, h = (_caret_x(st["chars"]) - 64) * 0.09, -3.0, 0.85
    if st["think"] and t < sum(st["think"]):
        u, d = t - st["think"][0], st["think"][1]
        k = smoothstep(min(u / 0.25, 1.0, (d - u) / 0.25))
        gx, gy = gx * (1 - k) - 7 * k, gy - 3 * k
    if st["typo"]:
        h -= 0.25
    if st["save"] is not None and t - st["save"] < 0.5:
        gy += 2.5 * math.sin(math.pi * (t - st["save"]) / 0.5)
    return gx, gy, h


ACTION = Action("editing", mood="focused", pose=_pose, overlay=_overlay)


if __name__ == "__main__":
    kinds = set()
    for s in range(300):
        ev = _script(s)
        kinds |= {k for _, k, _ in ev}
        assert ev[-1][1] == "enter" and ev[-1][0] + _SCROLL <= _STRETCH, "every stretch ends on a fresh line"
        assert ev[-2][1] == "save", "...saved"
        widest = 0
        chars = []
        for at, k, arg in ev:
            if k in ("key", "space"):
                chars.append(1)
            elif k == "bs":
                chars = chars[:-1]
            elif k == "cut":
                chars = chars[:-arg]
            elif k == "enter":
                chars = []
            elif k == "indent":
                chars = [0] * arg
            widest = max(widest, _caret_x(chars))
        assert widest <= _MAX_X + 2 * _CELL, f"lines stay on screen: {widest}"
        assert chars == [], "and the stretch ends empty"
    assert kinds == {"key", "space", "bs", "typo", "sel", "cut", "think", "save", "enter", "indent"}, kinds
    print("editing ok")
