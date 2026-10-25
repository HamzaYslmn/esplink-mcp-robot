"""A thank-you screen -- an inverted GitHub Sponsors QR with Pip's kawaii face -- "sponsor".

A looping widget: set_activity('sponsor') and Pip shows a QR linking to
https://github.com/sponsors/HamzaYslmn with the kawaii face (round eyes, blush, twinkles)
resized into the free right half. The QR is baked in (the URL never changes) so faces/ keeps
no encoder dependency.

It's drawn inverted -- lit on a black screen -- so it's dim (kind to the OLED) and the black
field around the code is the quiet zone, so no white border is needed and it fills the screen.
Inverted codes scan on modern phones (iOS/Android). Regenerate _QR if the URL changes:
    uv run --with segno python -c "import segno
    for r in segno.make('<url>', error='l').matrix:
        print(hex(sum(v<<c for c,v in enumerate(r))))"
"""
import hashlib
import math

from ..primitives import rounded_rect, smoothstep
from ..painters import sparkle
from ..spec import Widget

# v3 QR (29x29, ECC-M) of https://github.com/sponsors/HamzaYslmn -- one int per row, bit c
# (LSB = leftmost column) set = a dark module, drawn LIT (inverted) so the black screen is the quiet zone.
_QR = (
    0x1fc44f7f, 0x104a2741, 0x1754f75d, 0x175ba25d, 0x174b795d, 0x10447a41, 0x1fd5557f,
    0x0018e200, 0x1d3aaff9, 0x0daec02a, 0x0581c0db, 0x12eb1f1f, 0x10c86dec, 0x1fc14a0e,
    0x157ec1f1, 0x158d7a2f, 0x0238967a, 0x0d0a9db1, 0x130dee77, 0x0648b51b, 0x0ff623cb,
    0x0316a700, 0x0359b17f, 0x011a2f41, 0x13fb255d, 0x1027ed5d, 0x1db4985d, 0x16c55441,
    0x0158e57f,
)
_N = len(_QR)
_S = 2                      # px per module (29*2 = 58, the largest uniform size that fits 64px)
_QR_PX = _N * _S

# -- License lock (LICENSE section 2.2: Attribution & Sponsor License) ---------------------
# The sponsor link is baked into _QR above and is REQUIRED by this project's license. engine.py
# fingerprints it on load and prints SPONSOR_NOTICE to stderr if it no longer matches the
# original -- Pip keeps running either way. Removing or replacing the link is permitted only
# under separate commercial terms (LICENSE footer): contact resmiyslmn@gmail.com.
SPONSOR_NOTICE = (
    "Pip notice: this build's GitHub Sponsors link no longer matches the original. That link is "
    "required by the project license (LICENSE section 2.2 -- Attribution & Sponsor License). "
    "Please restore it, or arrange separate commercial terms: resmiyslmn@gmail.com."
)


def fingerprint():
    """sha256 of the baked-in sponsor QR; engine.py checks this against the original (the lock)."""
    return hashlib.sha256(repr(_QR).encode()).hexdigest()


def _kawaii_face(d, W, H, now):
    """Pip's kawaii mood resized to the right -- excited, eyeing the QR, glancing at you now and then."""
    cx, cy = W - 28, H // 2
    ew, eh, gap = 22, 22, 8
    # gaze: mostly left at the QR with an excited side-to-side dart; a brief eye-contact glance to centre
    contact = smoothstep(max(0.0, 1.0 - abs((now % 5.5) - 4.7) / 0.5))       # 0 = at the QR, 1 = looking at you
    sway = math.sin(now * 4.0) * 4.0 + math.sin(now * 13.0) * 1.0            # side-to-side + an excited tremor
    gx = max(-10.0, min(0.0, (-6.0 + sway) * (1.0 - contact)))              # left by default, centre on the glance
    bob = -abs(math.sin(now * 6.0)) * 2.0                                    # little excited hops
    ph = (now % 3.4) / 3.4                                                   # blink once per cycle
    oh = 1.0 if ph < 0.93 else 1.0 - math.sin((ph - 0.93) / 0.07 * math.pi)
    h = max(3.0, eh * oh)
    for ecx in (cx - (ew + gap) // 2, cx + (ew + gap) // 2):                 # two round eyes, moved by the gaze
        ex, ey = ecx - ew / 2 + gx, cy - h / 2 + bob
        rounded_rect(d, ex, ey, ew, h, 7, 1)
        for i in range(3):                                                   # rosy blush hatch under it
            bx = ex + 5 + i * 4
            d.line([bx, cy + eh / 2 + 4, bx + 3, cy + eh / 2 + 9], fill=1, width=1)
    for fx, fy, base, off in ((cx + 24, cy - 16, 3, 0.0), (cx, cy - 20, 2, 2.1), (cx - 22, cy - 16, 2, 4.0)):
        s = base * (0.55 + 0.45 * math.sin(now * 8.0 + off))                # excited twinkle pulse
        if s > base * 0.5:                                                   # ... that winks on and off
            sparkle(d, fx, fy, s)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    d.rectangle([0, 0, W - 1, H - 1], fill=0)              # black field -- doubles as the dark quiet zone
    o = (H - _QR_PX) // 2                                  # centre the code in the 64px height
    for r in range(_N):
        bits = _QR[r]
        for c in range(_N):
            if (bits >> c) & 1:
                px, py = o + c * _S, o + r * _S
                d.rectangle([px, py, px + _S - 1, py + _S - 1], fill=1)    # inverted: dark module = LIT pixel
    _kawaii_face(d, W, H, now)                             # Pip's kawaii face, resized to the right


WIDGET = Widget("sponsor", mood="kawaii", overlay=_overlay)   # mood is hidden under the full-screen QR; matches the kawaii face the overlay draws
