"""A crash fit -- corruption tears the eyes apart (Watch Dogs style) -- "glitch".

A self-ending state: set_activity('glitch') and it corrupts until it rolls out -- `_expired`
below flips a coin every 3s for a 50% chance to settle back to normal (or idle to stop it
sooner). Self-contained -- the beat painters, the beat list, the nervous eye jitter, the
on-frame corruption, and the self-end roll all live here. Each beat painter shares
(d, img, W, H, t, seed, amp); img None -> the pixel-movers no-op."""
import math

from PIL import ImageChops

from ..primitives import frame, rand
from ..spec import Action

_BEAT = 0.07   # seconds per corruption beat
_AMP  = 6      # pixel shift the tears reach
_ROLL = 3.0    # seconds per self-end roll
_HEAL_ODD = 0.5    #  a coin flip with _HEAL_ODD chance to settle back to normal


def _datamosh(d, img, W, H, t, seed, amp):
    """Yank a few horizontal slices of the frame sideways -- the classic datamosh tear."""
    if img is None:
        return
    for k in range(3):
        y = (seed * 13 + k * 29) % (H - 4)
        h = 2 + (seed + k) % 4
        dx = (seed * 7 + k * 17) % (2 * amp + 1) - amp
        strip = img.crop((0, y, W, y + h))
        img.paste(0, (0, y, W, y + h))                       # clear the band, then drop it back shifted
        img.paste(strip, (dx, y))


def _displace_blocks(d, img, W, H, t, seed, amp):
    """Shove a couple of rectangular blocks off-register."""
    if img is None:
        return
    for k in range(2):
        bw, bh = 16 + (seed * 5 + k * 11) % 22, 6 + (seed * 3 + k * 7) % 12
        x = (seed * 9 + k * 23) % max(1, W - bw)
        y = (seed * 4 + k * 19) % max(1, H - bh)
        dx = (seed * 7 + k * 13) % (2 * amp + 1) - amp
        img.paste(img.crop((x, y, x + bw, y + bh)), (x + dx, y))


def _scanlines(d, img, W, H, t, seed, amp):
    """Carve CRT scanlines and drop a chunky static band over them."""
    for y in range(seed % 3, H, 3):
        d.line([0, y, W, y], fill=0, width=1)
    u, by = 4, int(abs(math.sin(seed * 0.13)) * (H // 4)) * 4
    for c in range(W // u):
        if rand(c, seed) > 0.5:
            d.rectangle([c * u, by, c * u + u - 1, by + u - 1], fill=1)


def _ghost(d, img, W, H, t, seed, amp):
    """OR an offset copy of the frame on top -- double-vision ghosting."""
    if img is None:
        return
    img.paste(ImageChops.lighter(img, ImageChops.offset(img, amp, 0)), (0, 0))


def _code_rain(d, img, W, H, t, seed, amp):
    """Stream short vertical dashes down the screen -- Matrix code-rain."""
    for col in range(6):
        x = 6 + col * (W - 12) // 5
        head = (t * (20 + (seed + col * 7) % 14) + col * 3.3) % (H + 10) - 5
        for j in range(4):
            y = int(head - j * 5)
            if 0 <= y < H:
                d.line([x, y, x, y + 3], fill=1, width=1)


def _invert_flash(d, img, W, H, t, seed, amp):
    """Flip the whole frame for a hard glitch pop."""
    if img is None:
        return
    img.paste(ImageChops.invert(img.convert("L")).convert("1"), (0, 0))


# the state cycles through these beats in order; None = a clean flicker gap between bursts
_BEATS = (_datamosh, _scanlines, None, _displace_blocks, _code_rain, None,
          _datamosh, _ghost, _invert_flash, None, _displace_blocks, _scanlines,
          None, _code_rain, _datamosh, None, _ghost, _displace_blocks, None,
          _scanlines, _datamosh, None)


def _pose(now):   # nervous eye jitter -- chunky kicks on active beats, still on the gaps
    f = int(now / _BEAT) % len(_BEATS)
    if _BEATS[f] is None:                                    # clean beat -> hold steady
        return 0.0, 0.0, 1.0
    jx = rand(f)                                             # per-beat pseudo-random 0..1
    jy = rand(f, 7)                                          # a salt -> an independent stream
    return (round(jx * 4) - 2) * 3, (round(jy * 2) - 1) * 2, 1.0   # kick the gaze sideways/up


def _overlay(d, W, H, now, ox=0.0, oy=0.0):   # paint this beat's corruption onto the live frame
    f = int(now / _BEAT) % len(_BEATS)
    effect = _BEATS[f]
    if effect:
        effect(d, frame(d), W, H, now, f * 7 + 1, _AMP)


def _expired(now, start):   # roll a die each 3s window; a 50% hit ends the fit, seeded by the start
    k = int((now - start) / _ROLL)                          # window index (0 = before the first roll)
    return k >= 1 and rand(start + k * 7.31) < _HEAL_ODD


ACTION = Action("glitch", mood="scared", pose=_pose, overlay=_overlay, expired=_expired)
