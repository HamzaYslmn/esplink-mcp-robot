"""Gaze down at the Docker container-whale riding a live sea -- deploying."""
import math

from PIL import Image, ImageDraw, ImageFilter

from ..primitives import frame, rand
from ..spec import Action


def _make_spectrum():
    # seven swells at random lengths/speeds/phases, built once -- summed live they never repeat,
    # so the surface is always alive: crests wander, overtake and merge. (k, omega, phase, base-amp);
    # long waves run faster -- deep-water dispersion omega = sqrt(g*k).
    waves = []
    for i in range(7):
        k = 2 * math.pi / (15 + rand(i) * 90)                  # random 15..105px wavelength
        waves.append((k, math.sqrt(5.0 * k) * (0.9 + 0.2 * rand(i + 13)),
                      rand(i + 23) * 6.283, 0.25 + 0.8 * rand(i + 7)))
    return waves


_SPECTRUM = _make_spectrum()   # constant; only each wave's amplitude rides the wind, scaled per frame


def _pose(now):   # gaze down at the container-whale bobbing on the swell, drifting with it
    return math.sin(now * 0.25) * 4, 7 + math.sin(now * 1.7) * 1.2, 1.0


def _overlay(d, W, H, now, ox=0.0, oy=0.0):  # the Docker whale -- a 'D' stacked with containers, riding a live sea -- "deploying"
    # the wind rises and falls over ~tens of seconds; two incommensurate cycles keep the weather
    # from ever looking periodic. 0 = glassy calm, 1 = choppy gale -> sets how tall the waves run.
    sea_at = lambda t: max(0.0, min(1.0, 0.5 + 0.34 * math.sin(t * 0.06) + 0.16 * math.sin(t * 0.015 + 1.3)))
    sea, wl = sea_at(now), H - 4                                   # wind 0..1, and the mean waterline
    amp = 0.4 + sea                                                # the wind scales every wave's height
    height = lambda x: sum(ba * amp * math.sin(k * x - w * now + ph) for k, w, ph, ba in _SPECTRUM)
    surf = lambda x: wl + height(x)                               # the live, multi-wave sea surface

    # the hull drifts downwind: right as the sea builds, easing back left as it calms (with inertia,
    # so the berth trails the weather by a beat). then each wave's orbit nudges it fore-and-aft.
    berth = W / 2 + (sea_at(now - 3.0) - 0.5) * 34                # calm -> left of centre, building -> right
    cx = berth + sum(ba * amp * math.cos(k * berth - w * now + ph) for k, w, ph, ba in _SPECTRUM) * 0.5
    sy = surf(cx)                                                 # floats on whatever wave is under it (buoyancy)
    pitch = math.degrees(math.atan(sum(ba * amp * k * math.cos(k * cx - w * now + ph)
                                       for k, w, ph, ba in _SPECTRUM))) * 0.45  # tilts to the slope -> rolls hard in chop

    # paint the whale on a scratch layer: lets us pitch it, clip its belly at the water, then stamp
    # a 1px black outline so its white hull stays distinct from the white eyes
    lay = Image.new("1", (W, H), 0)
    g = ImageDraw.Draw(lay)
    deck = sy - 11                                                 # the flat deck -- the straight back of the 'D'
    g.chord([cx - 24, deck - 13, cx + 16, deck + 13], 0, 180, fill=1)              # body: a 'D' laid on its back
    g.polygon([(cx + 10, deck + 1), (cx + 22, deck - 10), (cx + 16, deck + 1)], fill=1)  # tail: upper fluke
    g.polygon([(cx + 15, deck - 6), (cx + 24, deck - 3), (cx + 16, deck + 1)], fill=1)   # tail: lower fluke
    cw, ch, scx = 8, 4, cx - 5                                     # container size + stack centre
    for r, n in enumerate((4, 3, 1)):                            # a 4-3-1 stack of plain containers, lying flat
        x0, yt = scx - n * cw / 2, deck - (r + 1) * ch
        for c in range(n):
            bx = x0 + c * cw
            g.rectangle([bx, yt, bx + cw, yt + ch], fill=1, outline=0)   # black edge -> a gap between each box
    g.ellipse([cx - 20, deck - 3, cx - 18, deck - 1], fill=0)     # a small eye on the head

    lay = lay.rotate(pitch, resample=Image.NEAREST, center=(cx, sy))           # roll with the swell
    belly = [(x, surf(x)) for x in range(0, W + 1, 2)] + [(W, H), (0, H)]
    ImageDraw.Draw(lay).polygon(belly, fill=0)                                 # the belly dips into the water

    base = frame(d)
    base.paste(0, (0, 0), lay.convert("L").filter(ImageFilter.MaxFilter(3)).convert("1"))  # 1px black outline
    base.paste(1, (0, 0), lay)                                                             # then the white whale
    d.line([(x, surf(x)) for x in range(0, W + 1, 2)], fill=1, width=1, joint="curve")     # the sea surface, on top


ACTION = Action("deploying", mood="neutral", pose=_pose, overlay=_overlay)
