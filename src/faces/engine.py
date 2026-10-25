"""EyeEngine -- threaded renderer for the mood / gesture / activity layers. One move at a time
(blink or gesture); a separate eased pose glides gaze + size.

The pure eye math lives in primitives.py; this module keeps the renderer, the shared `look`
glance helper, and the license lock. Effects import primitives for math (not this module), and
the registries are pulled in lazily inside EyeEngine, so there's no import cycle."""
from __future__ import annotations

import math
import random
import sys
import threading
import time

from PIL import Image, ImageDraw

from .primitives import ease, lid_openness, rounded_rect, smoothstep

_TAU_GAZE, _TAU_SIZE = 0.09, 0.11            # gaze / eye-size settle time-constants
_AUTO = ({"left", "right"}, 0.20, 1)         # spontaneous blink (eyes, dur, reps)
_MASK = ({"left", "right"}, 0.24, 1)         # blink that hides a mood's lid swap
_BLINK_GAP, _IDLE_GAP = (2.0, 6.0), (1.5, 5.0)   # s between spontaneous blinks / idle glances

# License lock (LICENSE 2.2): sha256 of the original GitHub Sponsors QR baked into widgets/sponsor.py.
# On load the engine fingerprints that QR and, if it no longer matches, prints sponsor.SPONSOR_NOTICE
# to stderr -- a notice, never a block. The sponsor link is required by the license; removing it (which
# also means editing this constant) is permitted only under separate commercial terms.
_SPONSOR_FINGERPRINT = "4f93689635e17c20911891a195de5050b5b379f4ce815e7e460227ea4f64658b"
_sponsor_checked = False                     # print the notice at most once per process


# ----------------------------------------------------------- gesture motion helper
def look(dx, dy, bias=0.0):
    """A glance motion: dart to (dx, dy), parallax-swell the near eye, hold, then return.
    Returns a gesture motion fn(p, env); shared by the look_left/right/up/down gestures."""
    def fn(p, e):
        if p < 0.22:        # quick dart out
            hold = p / 0.22
        elif p > 0.80:      # quick return
            hold = (1.0 - p) / 0.20
        else:               # hold the look
            hold = 1.0
        hold = smoothstep(hold)               # ease the ramps
        s = 1.0 - 0.12 * hold                 # mild foreshorten (parallax carries the turn)
        return dx * hold, dy * hold, 0.0, s, s, bias * hold
    return fn


# ------------------------------------------------------ engine-internal helpers
def _progress(m, now):
    """Fraction of a move dict's (start, dur) elapsed -- unclamped, so >1 once finished."""
    return (now - m["start"]) / m["dur"]


def _expired(m, now):
    """A blink/gesture move dict has run past its duration (None -> not expired)."""
    return bool(m) and _progress(m, now) > 1.0


def _safe(fn, *args):
    """Run a fragile BLE/IO push; swallow a hiccup so the loop survives. True on success."""
    try:
        fn(*args)
        return True
    except Exception:
        return False


class EyeEngine:
    def __init__(self, show, *, width=128, height=64, fps=30,
                 eye_w=36, eye_h=36, radius=12, gap=10,
                 set_brightness=None, bright=255,          # bright = panel brightness, max by default
                 clock=time.monotonic):                    # swap for a virtual clock to render offline
        from . import LOOPING, MOODS, PLAYABLE             # pulled in here (not at module top) so effect
        # files can import the eye math above without a circular import back through the registries.
        # PLAYABLE = gestures + reactions (one-shots); LOOPING = actions + vibes + widgets (loops).
        self.MOODS, self.GESTURES, self.ACTIONS = MOODS, PLAYABLE, LOOPING
        self._verify_sponsor()                             # license lock: notice if the sponsor link was altered

        self._show, self._clock = show, clock
        self._set_brightness, self._bright = set_brightness, bright
        self._cur_bright = None                          # unset -> first frame pushes it
        self.W, self.H, self.fps = width, height, max(5, fps)
        self.eye_w, self.eye_h, self.radius, self.gap = eye_w, eye_h, radius, gap
        self.base_lx = (width - (2 * eye_w + gap)) // 2
        self.base_ly = (height - eye_h) // 2
        self._img = Image.new("1", (width, height), 0)   # one reused frame buffer
        self._draw = ImageDraw.Draw(self._img)

        self.gx = self.gy = 0.0                          # eased pose (thread-only)
        self.ew, self.eh = float(eye_w), float(eye_h)
        self._last = 0.0                                  # time of the previous step (for dt)

        self._lock = threading.Lock()                    # guards the fields below
        self.mood = "neutral"
        self._pending = None                             # mood waiting for the layer to free
        self.look_x = self.look_y = 0.0                  # resting gaze target
        self._blink = self._gesture = self._activity = None
        self._activity_start = 0.0                        # clock time the current activity began
        self._next_blink = self._next_idle = self._next_tic = 0.0
        self._stop = threading.Event()
        self._thread = None

    # ------------------------------------------------------------------ API
    @staticmethod
    def _verify_sponsor():
        """License lock (LICENSE 2.2): if the baked-in sponsor link was altered, print the notice
        to stderr -- once per process -- and carry on. Never blocks Pip; silencing it means editing
        the link out, which the license permits only under separate commercial terms."""
        global _sponsor_checked
        if _sponsor_checked:
            return
        _sponsor_checked = True
        try:
            from .widgets import sponsor
            if sponsor.fingerprint() != _SPONSOR_FINGERPRINT:
                print(sponsor.SPONSOR_NOTICE, file=sys.stderr)
        except Exception:
            pass                                          # a missing/odd sponsor module never blocks startup

    def start(self):
        if not (self._thread and self._thread.is_alive()):
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, name="eye-engine", daemon=True)
            self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.5)

    def set_mood(self, mood):
        m = mood.lower() if mood and mood.lower() in self.MOODS else "neutral"
        with self._lock:
            self._activity = None                        # an emotion owns the face alone -- drop any looping action
            if m == self.mood:
                self._pending = None
            elif self._blink or self._gesture:           # busy -> apply (masked) once free
                self._pending = m
            else:
                self.mood = m
                self._begin_blink(self._clock(), _MASK)

    def play_gesture(self, name):
        """Play a commanded blink/gesture; preempts whatever's on the moving layer."""
        with self._lock:
            self._play(name, self._clock())

    def _play(self, name, now):
        """Start a blink/gesture on the moving layer (caller holds the lock; unknown -> no-op)."""
        g = self.GESTURES.get((name or "none").lower())
        if g is None:
            return
        if g.blink:
            self._begin_blink(now, (g.blink[0], g.dur, g.blink[1]))
        else:                                            # enveloped motion
            self._blink = None
            self._gesture = {"kind": g.name, "start": now, "dur": g.dur}
            self._next_blink = now + g.dur + random.uniform(*_BLINK_GAP)   # no spontaneous blink piling on

    def set_activity(self, name):
        """Loop a status animation ('idle'/unknown stops it). The action wears its OWN fitting
        face while it runs (see _face); the held emotional mood is left untouched and resumes
        when it ends -- the two layers never blend."""
        act = (name or "idle").lower()
        with self._lock:
            self._activity = act if act in self.ACTIONS else None
            self._activity_start = self._clock()
            tic = self.ACTIONS[self._activity].tic if self._activity else None
            if tic:                                       # align the periodic gesture to its period grid
                self._next_tic = (int(self._activity_start / tic[1]) + 1) * tic[1]

    def show(self, name):
        """Route any effect name to the right layer: a held mood, a one-shot move, or a loop
        ('idle'/unknown clears the loop). The single name-router tools.face and record_gif share."""
        n = (name or "").lower()
        if n in self.MOODS:
            self.set_mood(n)                  # held expression
        elif n in self.GESTURES:              # PLAYABLE pool: gestures + reactions (one-shots)
            self.play_gesture(n)
        else:
            self.set_activity(n)              # LOOPING pool, or 'idle'/unknown -> stop

    def _face(self, mood, act):
        """The mood actually rendered: an active action wears its own fitting face,
        else the held emotional mood. (Caller passes a locked snapshot.)"""
        if act and self.ACTIONS[act].mood:
            return self.ACTIONS[act].mood
        return mood

    # ----------------------------------------------------------- frame loop
    def _begin_blink(self, now, spec):
        """Start a blink, clearing the moving layer; reschedule the next spontaneous blink
        for after it ends so one never piles on this move (caller holds the lock)."""
        eyes, dur, reps = spec
        self._gesture = None
        self._blink = {"eyes": set(eyes), "start": now, "dur": dur, "reps": reps}
        self._next_blink = now + dur + random.uniform(*_BLINK_GAP)

    def reset_timers(self, now):
        """Seed the step clock and the next spontaneous blink/glance (call before stepping)."""
        self._last = now
        self._next_blink = now + random.uniform(*_BLINK_GAP)
        self._next_idle = now + random.uniform(*_IDLE_GAP)

    def step(self, now):
        """Advance one frame to time `now` and return the rendered buffer (no hardware push)."""
        dt = min(0.1, now - self._last)                   # clamp so a stall can't teleport the eyes
        self._last = now
        mood, act, look_at = self._schedule(now)
        self._ease_pose(now, dt, mood, act, look_at)
        return self._render(now)

    def _loop(self):
        self.reset_timers(self._clock())
        frame = 1.0 / self.fps
        while not self._stop.is_set():
            now = self._clock()
            _safe(lambda: self._show(self.step(now)))     # bad effect frame / BLE hiccup -> skip it, keep the loop alive
            time.sleep(max(0.0, frame - (self._clock() - now)))

    def _schedule(self, now):
        """Locked: retire finished moves, fire the next auto blink/glance, snapshot state."""
        with self._lock:
            if _expired(self._blink, now):
                self._blink = None
            if _expired(self._gesture, now):
                self._gesture = None
            if self._activity:                               # let an activity that defines `expired` self-end
                expired = self.ACTIONS[self._activity].expired
                if expired and expired(now, self._activity_start):
                    self._activity = None                    # it decided it's done -> back to normal
            free = not (self._blink or self._gesture)
            face = self._face(self.mood, self._activity)  # the mood actually on screen (action's, else held)
            act = self._activity                          # an action may also hold still (jackpot's reels)
            still = self.MOODS[face].still or (act is not None and self.ACTIONS[act].still)
            tic = self.ACTIONS[act].tic if act else None  # action's periodic gesture (e.g. a wink)
            if free and self._pending:                    # masked deferred mood swap
                self.mood, self._pending = self._pending, None
                self._begin_blink(now, _MASK)
            elif free and tic and now >= self._next_tic:  # action's own beat -> play it on the move layer
                name = tic[0](now)                        # resolver -> a gesture name, or None to skip
                if name:
                    self._play(name, now)
                while self._next_tic <= now:              # stay on the period grid (synced to the overlay)
                    self._next_tic += tic[1]
            elif free and now >= self._next_blink:        # spontaneous blink (unless mood holds still)
                if still:
                    self._next_blink = now + random.uniform(*_BLINK_GAP)   # zen: just reschedule, no blink
                else:
                    self._begin_blink(now, _AUTO)                   # reschedules _next_blink itself
            elif free and self._activity is None and now >= self._next_idle:   # idle glance
                centered = random.random() < 0.3
                self.look_x, self.look_y = (0.0, 0.0) if centered else \
                    (random.uniform(-16, 16), random.uniform(-7, 7))
                if not centered and random.random() < 0.4:        # eyes tend to blink as they dart
                    self._begin_blink(now, _AUTO)
                self._next_idle = now + random.uniform(*_IDLE_GAP)
            if still:                                     # a still mood holds its gaze centred (zen)
                self.look_x = self.look_y = 0.0
            return face, self._activity, (self.look_x, self.look_y)

    def _ease_pose(self, now, dt, mood, act, look_at):
        """Push brightness, then glide gaze + eye-size toward target."""
        spec = self.MOODS[mood]
        bright = self._bright if spec.bright is None else min(spec.bright, self._bright)   # emote may dim, capped at max
        if self._set_brightness and bright != self._cur_bright and _safe(self._set_brightness, bright):
            self._cur_bright = bright                     # record only what actually pushed -> retry next frame on a hiccup
        if act:
            a = self.ACTIONS[act]
            tx, ty, hmult = a.pose(now) if a.pose else (0.0, 0.0, 1.0)
        else:
            tx, ty, hmult = look_at[0], look_at[1], 1.0
        self.gx = ease(self.gx, tx, dt, _TAU_GAZE)
        self.gy = ease(self.gy, ty, dt, _TAU_GAZE)
        self.ew = ease(self.ew, self.eye_w + spec.dw, dt, _TAU_SIZE)
        self.eh = ease(self.eh, (self.eye_h + spec.dh) * hmult, dt, _TAU_SIZE)

    # --------------------------------------------------------- motion + draw
    @staticmethod
    def _breath(now, amp):
        """Slow breath -> (vertical bob px, eye-height multiplier)."""
        period, bob_px, swell = 3.7, 1.0, 0.018           # s/cycle, px rise/fall, height swell
        w = 2 * math.pi / period
        bob = math.sin(now * w) * bob_px * amp
        return bob, 1.0 + swell * math.sin(now * w - 0.5) * amp   # swell lags the bob -> "inflate"

    @staticmethod
    def _drift(now):
        """Slow incommensurate gaze wander so a resting face never locks -> (x, y) px."""
        ax, ay = 0.5, 0.32                                # px wander amplitudes
        x = (math.sin(now * 0.61) + 0.5 * math.sin(now * 1.07 + 1.2)) * ax
        y = (math.sin(now * 0.73 + 2.0) + 0.5 * math.sin(now * 1.31)) * ay
        return x, y

    def _idle_life(self, now, spec, busy):
        """Breath always + a slow gaze wander at rest -> (x, y incl. bob, breath mult)."""
        calm = spec.still
        amp = 0.4 if busy else (0.55 if calm else 1.0)
        bob, breath = self._breath(now, amp)
        if busy or calm:
            return 0.0, bob, breath                       # no wander while busy / meditating
        dx, dy = self._drift(now)
        return dx, bob + dy, breath

    @staticmethod
    def _blink_lids(b, now):
        """Per-eye openness (snaps shut, eases open); (1, 1) at rest."""
        if not b:
            return 1.0, 1.0
        o = lid_openness(_progress(b, now), b["reps"])
        ol = o if "left" in b["eyes"] else 1.0
        or_ = o if "right" in b["eyes"] else 1.0
        return ol, or_

    def _gesture_move(self, g, now):
        """Gesture motion -> (dx, dy, conv, w-scale, h-scale, bias); rest with none."""
        if not g:
            return 0.0, 0.0, 0.0, 1.0, 1.0, 0.0
        ph = min(1.0, _progress(g, now))
        ret = self.GESTURES[g["kind"]].motion(ph, math.sin(ph * math.pi))   # env = sin fades it in/out
        return (*ret[:5], ret[5] if len(ret) > 5 else 0.0)

    @staticmethod
    def _tilt(spec, now):
        """Per-eye y-skew: static tilt + optional animated `sway` (woozy seesaw)."""
        tilt = spec.tilt
        if spec.sway:
            amp, spd = spec.sway
            tilt += amp * math.sin(now * spd)
        return tilt

    def _draw_eye(self, sx, y0, openness, right, tilt, bias, conv, sw, sh, breath, paint):
        """Draw one eye: parallax + gesture scale + breath, shut centred, then mood lids."""
        es = 1.0 + (bias if right else -bias)             # parallax: the near eye swells
        w = max(2.0, self.ew * sw * es)
        ho = max(2.0, self.eh * sh * es * breath)         # open height (before the blink)
        h = max(2.0, ho * openness)
        ex = sx + (self.eye_w - w) / 2 + (-conv if right else conv)
        ey = y0 + (tilt if right else -tilt) + (self.eye_h - h) / 2   # blink shrinks toward centre
        r = min(w, h) * self.radius / self.eye_w
        rounded_rect(self._draw, ex, ey, w, h, r, 1)
        if paint:                                         # lids are the eye's shape -> keep them through a blink
            paint(self._draw, ex, ey, w, h, r, right)

    def _draw_extras(self, now, spec, act):
        """Mood decor, then the activity overlay."""
        d = self._draw
        if spec.decor:
            spec.decor(d, self.W, self.H, now, self.gx, self.gy)
        a = self.ACTIONS.get(act)
        if a and a.overlay:
            a.overlay(d, self.W, self.H, now, self.gx, self.gy)      # pass gaze so a prop rides the face

    def _render(self, now):
        with self._lock:                                 # snapshot; dicts are never mutated in place
            mood, act, b, g = self.mood, self._activity, self._blink, self._gesture
        spec = self.MOODS[self._face(mood, act)]          # action wears its own face; held mood otherwise

        ol, or_ = self._blink_lids(b, now)
        dx, dy, conv, sw, sh, gbias = self._gesture_move(g, now)
        tilt = self._tilt(spec, now)
        bias = spec.bias + gbias                         # + = right eye bigger, left smaller
        lifex, lifey, breath = self._idle_life(now, spec, g is not None or act is not None)

        self._draw.rectangle([0, 0, self.W - 1, self.H - 1], fill=0)   # clear the reused buffer
        if not spec.bare:                                              # 'bare' (cool) draws no eyes
            x0 = self.base_lx + self.gx + dx + lifex                   # left eye's slot origin
            y0 = self.base_ly + self.gy + dy + lifey
            paint = spec.paint
            for sx, openness, right in ((x0, ol, False),
                                        (x0 + self.eye_w + self.gap, or_, True)):
                self._draw_eye(sx, y0, openness, right, tilt, bias, conv, sw, sh, breath, paint)
        self._draw_extras(now, spec, act)
        return self._img
