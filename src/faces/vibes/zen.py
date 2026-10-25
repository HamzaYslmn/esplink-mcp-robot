"""Eyes softly shut + cherry blossoms on a living breeze -- in flow. (Wears `neutral`, held
nearly-shut and still via the pose, so the falling sakura carries the whole scene.)"""
import math

from ..primitives import rand
from ..spec import Vibe


def _pose(now):
    return 0.0, 0.0, 0.12          # gaze centred, eyes a soft shut line -- the blossoms do the rest


def _overlay(d, W, H, now, ox=0.0, oy=0.0):  # cherry blossoms on a living breeze -- "in flow"
    # each leaf falls at its own terminal speed and is carried right by the wind: light ones hang
    # and blow clear across (off the right edge), heavy ones drop to the floor. The breeze always
    # blows -- swelling gusts, soft lulls, never stalling -- so the leaves stream, never a waterfall.
    SHAPE = ((0.0, 1.05), (-0.5, 0.4), (-0.68, -0.3), (-0.5, -0.82), (-0.22, -0.98),  # notched sakura petal:
             (0.0, -0.46), (0.22, -0.98), (0.5, -0.82), (0.68, -0.3), (0.5, 0.4))     # pointed stem, V-notch at the tip
    G0 = 6.5                                                        # steady breeze (px/s), always rightward
    WIND = ((1.8, 0.10, 0.0), (0.9, 0.29, 1.7), (0.5, 0.73, 4.2))   # gusts (amp px/s, omega, phase); sum 3.2 < G0
    def push(t0, t1):                                              # px the breeze carries a leaf between two times
        s = G0 * (t1 - t0)
        for a, w, p in WIND:
            s += a * (math.cos(w * t0 + p) - math.cos(w * t1 + p)) / w
        return s
    windv = G0 + sum(a * math.sin(w * now + p) for a, w, p in WIND)  # live wind -> wider flutter in gusts
    for i in range(9):                                             # spawn slots; ~3-5 on screen at once
        T = 14.0 + i % 4 * 2.0                                     # this slot's spawn cycle (14..20s)
        u = now / T + i * 0.41
        cyc = int(u)
        el = (u - cyc) * T                                        # cycle index + seconds since this leaf spawned
        r = lambda n: rand(i * 9 + cyc * 131 + n * 7.1)       # re-rolled each spawn (shared hash)
        m = r(0)                                                   # weight: 0 light .. 1 heavy
        vfall = 6.0 + m * 10.0                                     # terminal fall (px/s): light hangs, heavy drops
        sail = 0.5 + (1 - m) * 1.7 + r(1) * 0.7                    # wind catch: light catches more + its own "sail"
        lag = m * 0.6 + r(2) * 0.6                                 # heavy lags the gust; each feels it at its own moment
        fph = el * (2.0 + (1 - m) * 3.0) + r(3) * 6              # falling-leaf flutter phase (light = faster)
        x = -10 + r(4) * W * 0.35 + sail * push(now - lag - el, now - lag) \
            + math.sin(fph) * (1.8 + (1 - m) * 3.2) * (0.6 + windv * 0.07)   # spawn-left + wind drift + flutter sway
        y = -7 + r(5) * 5 + vfall * el + math.sin(fph * 0.5) * 1.6 * (1 - m)  # fall from the top + a faint flutter bob
        if x > W + 9 or y > H + 9:                                # off the right or the floor -> gone till it respawns
            continue
        ang = el * (0.5 + (1 - m) * 1.3) * (1 if r(6) > 0.5 else -1) + math.cos(fph) * 0.6 + r(7) * 6  # tumble + rock
        fore = 0.4 + 0.6 * abs(math.cos(el * (0.7 + (1 - m)) + r(8) * 6))    # pinch thin when edge-on -> a 3D flash
        wid, lng, bend = (2.4 + r(1) * 1.8) * fore, 3.0 + r(2) * 3.0, (r(6) - 0.5) * 0.9  # size + aspect + comma bow
        ca, sa = math.cos(ang), math.sin(ang)
        pts = []
        for px, py in SHAPE:
            bx, by = (px + bend * py * py) * wid, py * lng          # bow into a comma, then stretch to size/aspect
            pts.append((x + bx * ca - by * sa, y + bx * sa + by * ca))
        d.polygon(pts, fill=1)


VIBE = Vibe("zen", mood="neutral", pose=_pose, overlay=_overlay, still=True)
