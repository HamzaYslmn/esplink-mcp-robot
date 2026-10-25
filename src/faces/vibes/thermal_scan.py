"""Thermal scan -- Pip becomes a thermal camera. A bright scan bar sweeps the WHOLE screen
left<->right; both eyes glow as smooth hot cores (solid centre, thin dithered rim), the RIGHT eye
runs hotter under a pulsing target reticle + carved crosshair. Viewfinder corner brackets frame
it, with a crisp HUD: a THERMAL label and a live temperature.

Temp is read from a real DS18B20 on 1-wire (Raspberry Pi GPIO4 = the "D4" pin) via sysfs -- a
filled dot marks a live reading; with no sensor it falls back to a synthetic wander."""
import glob
import math

from PIL import ImageFont

from ..primitives import rand, smoothstep
from ..spec import Vibe

_EYE_W, _GAP = 36, 10                                         # engine defaults -> place the eyes
_REACH = 9.0                                                  # scan-bar heat reach (px)
_GLOW = 2.0                                                   # eye sharpening: solid core, thin dithered rim

# 4x4 Bayer matrix -> ordered dither thresholds; clean gradient instead of noisy speckle.
_BAYER = [[(v + 0.5) / 16.0 for v in row] for row in (
    (0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))]

try:
    _FONT = ImageFont.load_default(size=12)
except TypeError:                                             # ancient Pillow
    _FONT = ImageFont.load_default()

_cache = [-99.0, 0.0]                                         # last-read `now`, last value (C)
_real = [None]                                                # None=untried, True=live sensor, False=absent


def _parse_w1(txt):
    """DS18B20 sysfs blob -> degrees C (the 't=' millidegrees on the last line)."""
    return int(txt[txt.rfind("t=") + 2:]) / 1000.0


def _read_temp(now):
    """Live DS18B20 on 1-wire (RPi GPIO4 = 'D4'), cached ~2s. None if no sensor present."""
    if _real[0] is False:
        return None                                           # known absent -> stop hitting the FS
    if _real[0] and now - _cache[0] < 2.0:
        return _cache[1]
    try:
        with open(glob.glob("/sys/bus/w1/devices/28-*/w1_slave")[0]) as f:
            _cache[0], _cache[1], _real[0] = now, _parse_w1(f.read()), True
        return _cache[1]
    except Exception:                                         # ponytail: no sensor this session, never recheck
        _real[0] = False
        return None


def _pose(now):
    return 0.0, 0.0, 1.0                                      # centred -- the scan owns the screen


def _blob(dx, dy, rx2, ry2):
    q = dx * dx / rx2 + dy * dy / ry2                         # elliptical falloff -> eye-shaped heat
    return 1.0 - q if q < 1.0 else 0.0


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    d.rectangle([0, 0, W - 1, H - 1], fill=0)                 # own the canvas -> thermal cold = black

    base_lx = (W - (2 * _EYE_W + _GAP)) // 2
    lcx = base_lx + _EYE_W / 2 + ox                           # eye heat-source centres (ride the gaze)
    rcx = base_lx + 1.5 * _EYE_W + _GAP + ox
    cy = H / 2 + oy
    rx2, ry2 = 12.5 ** 2, 16.0 ** 2                           # eyes a touch taller than wide

    t = (now * 0.5) % 1.0
    sweep = smoothstep(1.0 - abs(2 * t - 1.0)) * (W - 1)      # eased L<->R bounce across full width
    core_hot = 1.15 + 0.2 * (0.5 + 0.5 * math.sin(now * 6))   # right eye pulses hotter

    pts = []
    for x in range(W):
        gap = abs(x - sweep)
        reveal = smoothstep(1.0 - gap / _REACH) * 0.5 if gap < _REACH else 0.0   # bar lights cold area
        dxl, dxr = x - lcx, x - rcx
        for y in range(H):
            dy = y - cy
            hl = _blob(dxl, dy, rx2, ry2)
            hr = _blob(dxr, dy, rx2, ry2) * core_hot          # right eye runs hotter
            he = hl if hl > hr else hr
            h = he * _GLOW + reveal                           # _GLOW -> solid core, dither only the rim
            if h > _BAYER[y & 3][x & 3]:
                pts.append((x, y))
    if pts:
        d.point(pts, fill=1)

    d.line([sweep, 0, sweep, H], fill=1)                      # crisp full-height scan edge

    # Right eye = a locked target: bright pulsing ring out in the cool halo, a crosshair + inner
    # ring CARVED dark into the hot core so they read against the white.
    pr = 14.0 + 1.5 * (0.5 + 0.5 * math.sin(now * 6))
    d.ellipse([rcx - pr, cy - pr, rcx + pr, cy + pr], outline=1)
    d.ellipse([rcx - 6, cy - 6, rcx + 6, cy + 6], outline=0)
    d.line([rcx - 9, cy, rcx - 2, cy], fill=0)                # gapped crosshair, dark on the hot eye
    d.line([rcx + 2, cy, rcx + 9, cy], fill=0)
    d.line([rcx, cy - 9, rcx, cy - 2], fill=0)
    d.line([rcx, cy + 2, rcx, cy + 9], fill=0)

    for cxx, cyy, sx, sy in ((2, 2, 1, 1), (W - 3, 2, -1, 1),  # viewfinder corner brackets
                             (2, H - 3, 1, -1), (W - 3, H - 3, -1, -1)):
        d.line([cxx, cyy, cxx + 5 * sx, cyy], fill=1)
        d.line([cxx, cyy, cxx, cyy + 5 * sy], fill=1)

    real = _read_temp(now)                                    # live DS18B20, else synthetic wander
    temp = real if real is not None else 36.4 + 1.6 * math.sin(now * 0.3)
    tx, ty = 10, H - 14
    if real is not None:
        d.ellipse([10, H - 11, 14, H - 7], fill=1)            # filled dot = live sensor
        tx = 18
    num = f"{temp:.1f}"
    d.text((tx, ty), num, font=_FONT, fill=1)                 # value
    dx = tx + int(_FONT.getlength(num)) + 2
    d.ellipse([dx, ty + 1, dx + 3, ty + 4], outline=1)        # hand-drawn degree ring (font has no degree)
    d.text((dx + 5, ty), "C", font=_FONT, fill=1)


VIBE = Vibe("thermal_scan", mood="focused", pose=_pose, overlay=_overlay, still=True)


if __name__ == "__main__":                                   # ponytail check: the sysfs parse
    sample = "a1 01 4b 46 7f ff 0c 10 fc : crc=fc YES\na1 01 4b 46 7f ff 0c 10 fc t=26062\n"
    assert abs(_parse_w1(sample) - 26.062) < 1e-9, _parse_w1(sample)
    print("ok")
