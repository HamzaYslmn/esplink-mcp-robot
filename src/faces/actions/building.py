"""Three cubes fly in, stack, then tumble off -- building."""
import math

from ..primitives import rand, smoothstep
from ..spec import Action


def _pose(now):   # watching the cubes fly in and stack up in the centre
    return math.sin(now * 1.5) * 1.5, 4 + math.sin(now * 2.0) * 1.5, 0.92


def _cube(d, cx, cy, s):
    # one small 3D cube: white faces + black edges, so it reads over the eyes AND the dark bg
    h, o = s / 2, s * 0.42                                            # half-side, iso depth (up-right)
    x0, y0, x1, y1 = cx - h, cy - h, cx + h, cy + h
    d.polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill=1, outline=0)                  # front face
    d.polygon([(x0, y0), (x0 + o, y0 - o), (x1 + o, y0 - o), (x1, y0)], fill=1, outline=0)  # top face
    d.polygon([(x1, y0), (x1 + o, y0 - o), (x1 + o, y1 - o), (x1, y1)], fill=1, outline=0)  # right face


def _overlay(d, W, H, now, ox=0.0, oy=0.0):  # 3 cubes fly in, stack, then tumble off -- "building"
    s, step, hold, fall, gap = 10, 0.5, 0.15, 0.6, 0.2               # cube size + phase timings
    asm = 3 * step
    T = asm + hold + fall + gap
    cyc, lp = int(now / T), now % T
    cx = W / 2
    slot_y = (H - 9, H - 9 - (s + 2), H - 9 - 2 * (s + 2))           # stack bottom -> top
    for i in range(3):
        ty = slot_y[i]
        if lp < asm:                                                 # assembling, one cube at a time
            start = i * step
            if lp < start:
                continue                                             # this cube hasn't entered yet
            k = smoothstep(min(1.0, (lp - start) / step))            # eased fly-in 0..1
            dirn = int(rand(cyc * 9.7 + i * 4.3) * 3)                # 0 left / 1 right / 2 top
            sx, sy = (-14, ty) if dirn == 0 else (W + 14, ty) if dirn == 1 else (cx, -14)
            x, y = sx + (cx - sx) * k, sy + (ty - sy) * k
        elif lp < asm + hold:                                        # the finished tower stands a beat
            x, y = cx, ty
        else:                                                        # collapse: spread out + gravity
            tc = (lp - asm - hold) / fall
            x, y = cx + (i - 1) * (38 + i * 12) * tc, ty + 70 * tc * tc
        _cube(d, x, y, s)


ACTION = Action("building", mood="focused", pose=_pose, overlay=_overlay)
