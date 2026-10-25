"""Eye the test tube on three rhythms: shake / bubble / gas -- testing."""
import math

from ..spec import Action


def _pose(now):   # eyeing the test tube bubbling away in the bottom-right corner
    return 5 + math.sin(now * 1.6) * 1.5, 5 + math.sin(now * 1.1) * 1.5, 0.95


def _overlay(d, W, H, now, ox=0.0, oy=0.0):  # test tube on 3 independent rhythms: shake/bubble/gas -- "testing"
    env = lambda n, thr, soft: max(0.0, min(1.0, (n - thr) / soft))  # slow signal -> 0..1, off below thr
    shake = env(math.sin(now * 0.8) + math.sin(now * 1.9 + 1.0), 0.85, 0.3)        # bursts of the jitters
    bubl = env(math.sin(now * 0.5 + 0.7) + math.sin(now * 1.27 + 2.4), -0.2, 0.55)  # the gentle baseline simmer
    gasl = env(math.sin(now * 0.41) + math.sin(now * 0.93 + 1.6), 0.65, 0.5)        # spells of venting gas
    jx = math.sin(now * 42) * 2.0 * shake                          # shake jitter, scaled by its envelope
    cx, top, bot, hw = W - 10 + jx, H - 30, H - 4, 5              # tube centre/top/bottom/half-width
    liq = top + 11                                                # liquid surface
    d.line([cx - hw, top, cx - hw, bot - hw], fill=1)            # left wall
    d.line([cx + hw, top, cx + hw, bot - hw], fill=1)            # right wall
    d.arc([cx - hw, bot - 2 * hw, cx + hw, bot], start=0, end=180, fill=1)  # rounded bottom
    d.rectangle([cx - hw + 1, liq, cx + hw - 1, bot - hw], fill=1)         # liquid column
    d.ellipse([cx - hw + 1, bot - 2 * hw, cx + hw - 1, bot], fill=1)       # fill the rounded base
    d.rectangle([cx - hw - 1, top - 4, cx + hw + 1, top], fill=1)          # cap / stopper
    d.line([cx - hw - 1, top - 2, cx + hw + 1, top - 2], fill=0)           # groove on the cap
    for i in range(3):                                           # bubbles rise only during a bubbling spell
        bt = (now * (0.6 + i * 0.17) + i * 0.31) % 1.0          # 0 at the base -> 1 at the surface
        by = (bot - hw) - bt * (bot - hw - liq)
        bx = cx + math.sin(now * 3 + i * 2) * (hw - 2.5)
        r = (0.8 + (i % 2)) * bubl                              # size fades in/out with the spell
        if r > 0.45:
            d.ellipse([bx - r, by - r, bx + r, by + r], fill=0)
    if gasl > 0.05:                                             # thin gas wisps only while venting
        for mx, wdt, spd, off in ((cx - 2, 1, 0.33, 0.0), (cx + 3, 2, 0.25, 0.55)):
            p = (now * spd + off) % 1.0                          # one emission cycle
            ln = (3 + min(p / 0.82, 1.0) * 21) * gasl           # grows short -> long, fades with the spell
            lift = max(0.0, (p - 0.82) / 0.18) * (ln + 8)      # then it breaks free and climbs off
            pts = [(mx + math.sin(f * 3.6 + now * 1.8) * (0.5 + f * 2.6), (top - 4 - lift) - f * ln)
                   for f in (j / 7 for j in range(8))]          # gentle drift, wider toward the tip
            d.line(pts, fill=1, width=wdt, joint="curve")


ACTION = Action("testing", mood="focused", pose=_pose, overlay=_overlay)
