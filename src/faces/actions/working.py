"""A cartoon smith: wind-up, a SMASH, sparks arc -- working."""
import math

from PIL import Image, ImageDraw, ImageFilter

from ..primitives import frame, smoothstep
from ..spec import Action


def _pose(now):   # heads-down smithing; the eyes brace + squint with each hammer blow
    hit = max(0.0, 1.0 - abs((now * 0.95) % 1.0 - 0.61) / 0.14)   # peaks at the strike (synced to hammer)
    return math.sin(now * 1.1) * 3, 3 + hit * 5, 0.85 - hit * 0.3


def _overlay(d, W, H, now, ox=0.0, oy=0.0):  # a cartoon smith: big wind-up, a SMASH, sparks arc -- "working"
    cx = W // 2
    ax, ay = cx + 3, H - 8                            # where the hammer strikes the glowing bar
    px, py = cx - 14, H - 21                          # wrist pivot, up-left of the anvil
    L = math.hypot(ax - px, ay - py)                  # handle length -> the head lands right on the bar
    up, down = math.radians(-72), math.atan2(ay - py, ax - px)   # raised high vs struck
    t = (now * 0.95) % 1.0                            # one swing per ~1.05s
    if t < 0.50:                                       # wind up, easing to a held top -- anticipation
        th = down + (up - down) * smoothstep(t / 0.42)
    elif t < 0.60:                                     # the SMASH -- snap down
        th = up + (down - up) * smoothstep((t - 0.50) / 0.10)
    else:                                             # land, then a damped recoil bounce
        b = (t - 0.60) / 0.40
        th = down - math.sin(b * math.pi) * (1 - b) * math.radians(24)
    since = t - 0.60 if t >= 0.60 else 1.0            # progress since the strike (1 = not yet)

    # paint the whole assembly onto a scratch layer, then stamp it with a 1px black outline so
    # its white strokes never merge into the white eyes underneath
    lay = Image.new("1", (W, H), 0)
    g = ImageDraw.Draw(lay)
    yf = ay + 2                                       # the anvil's face, just under the bar
    g.polygon([(cx - 9, yf), (cx + 10, yf), (cx + 10, yf + 2), (cx - 9, yf + 2)], fill=1)  # overhanging flat top
    g.polygon([(cx - 9, yf), (cx - 9, yf + 2), (cx - 15, yf + 1)], fill=1)                 # the horn (pointed, left)
    g.polygon([(cx - 6, yf + 2), (cx + 5, yf + 2), (cx + 8, H - 1), (cx - 8, H - 1)], fill=1)  # waist -> wider feet
    bw = 7 + max(0.0, 1.0 - since / 0.13) * 5         # the glowing bar -- spreads wide on the hit
    g.rectangle([round(ax - bw), ay, round(ax + bw), yf], fill=1)
    hx, hy = px + L * math.cos(th), py + L * math.sin(th)
    nx, ny = -math.sin(th), math.cos(th)             # head bar, perpendicular to the handle
    g.line([px, py, hx, hy], fill=1, width=2)        # handle
    g.line([hx - 7 * nx, hy - 7 * ny, hx + 5 * nx, hy + 5 * ny], fill=1, width=6)  # chunky head
    if since < 0.30:                                 # impact: a star pop, then sparks arc out under gravity
        if since < 0.09:
            for a in range(0, 360, 45):
                rr = 3 + since * 70
                g.line([ax, ay, ax + math.cos(math.radians(a)) * rr,
                        ay + math.sin(math.radians(a)) * rr * 0.5], fill=1, width=1)
        for k in range(8):
            a = math.radians(-156 + k * 18)
            spd = 100 + (k % 3) * 34
            vx, vy = math.cos(a) * spd, math.sin(a) * spd
            sx, sy = ax + vx * since, ay + vy * since + 150 * since * since
            if sy < ay - 0.5:
                g.line([sx, sy, sx - vx * 0.022, sy - vy * 0.022], fill=1, width=1)

    base = frame(d)
    base.paste(0, (0, 0), lay.convert("L").filter(ImageFilter.MaxFilter(3)).convert("1"))  # 1px black outline
    base.paste(1, (0, 0), lay)                                                             # then the white assembly


ACTION = Action("working", mood="focused", pose=_pose, overlay=_overlay)
