"""The contract a contributor fills in. Each effect is ONE file in moods/ gestures/ reactions/
actions/ vibes/ widgets/ exposing a single MOOD / GESTURE / REACTION / ACTION / VIBE / WIDGET;
the folder's __init__ assembles them in order.

There are six folders but only three *mechanics*: a held mood, a one-shot move, a looping
overlay. A `reaction` is just a one-shot move fired in response to the world or the user (a
sensor/event, or a reply like nod/refuse) rather than a self-initiated glance -- so it reuses
`Gesture`. A `vibe` (pure decoration) and a `widget` (live data) are both looping overlays that
carry no emotion -- so they reuse `Action`. The aliases at the bottom let each file read in its
own vocabulary while the engine keeps one dispatch per mechanic.

To add an effect: copy the nearest sibling file, edit it, then add its name to the ordered
list in that folder's __init__.py. Nothing else to wire. Every fn gets the clock as a `Now`: a
plain float, plus `now.t` (seconds into this play) and `now.seed` (fresh per play) -- so a one-shot
needs no start-tracking state, and ends itself with e.g. `expired=lambda now: now.t >= 5`."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


class Now(float):
    """The clock every effect fn gets: still a plain float (absolute seconds -- or a gesture's 0..1
    progress), so loops stay continuous; plus `.t` = seconds since THIS play began and `.seed` =
    fresh per play. A one-shot reads `now.t` for its timeline and `rand(now.seed, ...)` for
    per-trigger variety -- no start-tracking state of its own."""
    def __new__(cls, value, t, seed):
        n = super().__new__(cls, value)
        n.t, n.seed = t, seed
        return n


@dataclass(frozen=True)
class Mood:
    """A held expression: a size delta + an optional lid `paint` + an optional `decor` prop."""
    name: str
    dw: float = 0.0                      # eye-width delta from the resting size
    dh: float = 0.0                      # eye-height delta
    tilt: float = 0.0                    # static per-eye y-skew (one up, one down)
    sway: Optional[tuple] = None         # (amp, speed) -> animated tilt, a woozy seesaw
    bias: float = 0.0                    # size skew: + = right eye bigger, left smaller
    bright: Optional[int] = None         # panel brightness 0..255 (None = engine default)
    bare: bool = False                   # draw NO eyes -- decor carries the whole face (cool)
    still: bool = False                  # hold the gaze centred, no spontaneous blink (zen)
    paint: Optional[Callable] = None     # lid carver (d, x, y, w, h, r, is_right), fill=0
    decor: Optional[Callable] = None     # prop (d, W, H, now, ox, oy)


@dataclass(frozen=True)
class Gesture:
    """A one-shot move: a centred `blink`, OR an enveloped `motion`."""
    name: str
    dur: float                           # seconds the move lasts
    motion: Optional[Callable] = None    # fn(p, env) -> (dx, dy, conv, sw, sh[, bias])
    blink: Optional[tuple] = None        # (eyes set, closes) -- lid-only, no motion fn


@dataclass(frozen=True)
class Action:
    """A looping task status: a gaze `pose` + a fitting `mood` face + an `overlay` prop.
    Most loop until set to idle; an optional `expired` lets one decide to self-end."""
    name: str
    mood: object = None                  # the mood whose face it wears -- a name, or fn() -> name to change it
    pose: Optional[Callable] = None      # fn(now) -> (gaze_x, gaze_y, height_mult)
    overlay: Optional[Callable] = None   # looping prop (d, W, H, now, ox, oy)
    expired: Optional[Callable] = None   # fn(now) -> True once it should end itself (else loops), e.g. now.t >= 5
    still: bool = False                  # hold the gaze + no spontaneous blink while it runs (jackpot reels)
    tic: Optional[tuple] = None          # (fn(now)->gesture_name|None, period_s): play it every period (e.g. a wink)
    eyes: Optional[Callable] = None      # fn(d, x, y, w, h, is_right, now): restyle each eye as it's drawn (naruto_eyes)


# the role aliases (see the module docstring)
Reaction = Gesture
Widget = Action
Vibe = Action
