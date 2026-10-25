"""Leaned back, a lit cigarette at the lips with occasional drags -- smoking."""
import math

from ..primitives import rand, smoothstep
from ..spec import Vibe

drag_chance = 0.4    # probability of a drag per 10s window (0..1) -- set from outside to taste
_DUR = 4.2           # one drag's length (s)
# drag beats as fractions of _DUR -- end of: draw | lower | hold breath | exhale | (raise back)
_DRAW, _LOWER, _HOLD, _EXHALE = 0.18, 0.38, 0.46, 0.82


def _drag(now):
    """Progress 0..1 through this 10s window's drag, or None when just chilling. Shared by the
    gaze and the prop so the eyes and the cigarette always tell the same story."""
    win, tloc = int(now / 10), now % 10
    if rand(win) < drag_chance and tloc < _DUR:
        return tloc / _DUR
    return None


def _pose(now):   # the gaze tells the story: settle to draw, lift to exhale, else lazily look around
    drift_x = math.sin(now * 0.5) * 3.5
    drift_y = -2 + math.sin(now * 0.31) * 2
    p = _drag(now)
    if p is not None:
        if p < _HOLD:                                   # draw + lower + hold -> eyes settle low and narrow
            return drift_x * 0.4, drift_y + 2, 0.8
        if p < _EXHALE:                                 # exhale -> gaze lifts to follow the plume up
            return drift_x * 0.5, drift_y - 6 * smoothstep((p - _HOLD) / (_EXHALE - _HOLD)), 1.0
        return drift_x, drift_y, 1.0                    # raising back -> ease to rest
    # chilling: drift + the usual idle glances -- ease to a new spot every few seconds, often just resting
    slot = int(now / 3.4)                              # hold each glance ~3.4s, like the resting idle
    gx = gy = 0.0
    if rand(slot + 1, 0) > 0.35:                       # ~2/3 of slots glance somewhere, the rest rest centred
        gx, gy = (rand(slot + 1, 1) * 2 - 1) * 14, (rand(slot + 1, 2) * 2 - 1) * 6
    return drift_x + gx, drift_y + gy, 1.0


def _overlay(d, W, H, now, ox=0.0, oy=0.0):  # a lit cigarette at the lips; occasional drags -- "chill"
    p = _drag(now)
    if p is None:                                       # just holding it, a lazy curl rising
        away = inhale = 0.0
    elif p < _DRAW:                                     # drawing the breath in, cig still at the lips
        away, inhale = 0.0, smoothstep(p / _DRAW)
    elif p < _LOWER:                                    # lowering the hand away
        away, inhale = smoothstep((p - _DRAW) / (_LOWER - _DRAW)), 0.0
    elif p < _EXHALE:                                   # held low -- breath held, then exhaling
        away, inhale = 1.0, 0.0
    else:                                               # raising it back home
        away, inhale = 1.0 - smoothstep((p - _EXHALE) / (1 - _EXHALE)), 0.0

    dx, dy = away * 16, away * 6                         # after a drag, lower it down-and-RIGHT, well clear of the mouth
    hx, hy = W * 0.58 + ox + dx, H - 10 + oy + dy        # filter end (at the lips when home)
    tx, ty = W * 0.74 + ox + dx, H - 7 + oy + dy         # burning ember tip
    d.line([hx, hy, tx, ty], fill=1, width=4)           # short, thick stick
    glow = 2 + 2 * inhale + 0.4 * math.sin(now * 6)      # ember flares on the draw, with a faint live flicker
    d.ellipse([tx - glow, ty - glow, tx + glow, ty + glow], fill=1)   # glowing ember tip

    def curl(s):                                        # one slow laminar curl off the ember, scaled 0..1
        if s <= 0.03:
            return
        pts = [(tx + math.sin(f * 4.5 - now * 0.9) * (f * f * 8) * s, ty - 2 - f * (ty - 4) * s)
               for f in (i / 15 for i in range(16))]    # shrinks toward the ember as s -> 0
        d.line(pts, fill=1, width=2, joint="curve")

    if p is None:
        curl(1.0)                                       # at rest -> the full curl
    elif p < _DRAW:
        curl(1.0 - inhale)                              # draw -> the curl thins away to nothing
    elif p < _EXHALE:                                   # lowered/held -> a thin smolder trails the ember
        pts = [(tx + math.sin(f * 5 - now * 1.4) * (1 + f * 4), ty - 1 - f * 16)
               for f in (i / 9 for i in range(10))]
        d.line(pts, fill=1, width=1, joint="curve")
    else:
        curl(1.0 - away)                               # raising it back -> the curl builds up again

    if p is not None and _HOLD <= p < _EXHALE:         # exhale -> a soft plume billows from the mouth, drifting up-left
        mx, my = W * 0.58 + ox, H - 10 + oy             # the mouth -- where the cig rests when held home, not the lowered tip
        eq = (p - _HOLD) / (_EXHALE - _HOLD)            # 0..1 across the exhale
        rise = smoothstep(eq) * 1.7
        fade = 1.0 if eq < 0.4 else smoothstep((1.0 - eq) / 0.6)   # dissipates gently over a long tail
        for i in range(22):
            f = i / 21.0
            front = rise - f * 0.9
            if front <= 0:
                continue
            cxl = mx - f * 6 + math.sin(f * 3.4 + p * 4) * (2 + f * 10)   # drifts up-left, away from the cig
            spread = 3 + f * 16
            base = (2.5 + f * 8) * min(1.0, front * 2.4) * fade       # fade shrinks every puff toward the end
            for j in (-1, 0, 1):                        # a few puffs across the width -> a full, soft plume
                bx, by = cxl + j * spread * 0.5, my - f * (my + 2) - rise * 3
                rad = base * (1.0 - 0.28 * abs(j))
                if rad > 0.5:
                    d.ellipse([bx - rad, by - rad, bx + rad, by + rad], fill=1)


VIBE = Vibe("smoking", mood="chill", pose=_pose, overlay=_overlay)
