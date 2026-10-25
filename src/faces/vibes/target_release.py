"""Target release -- break lock: still one-eyed, the corner brackets fly back out to the screen
corners, then it self-ends to the natural face (both eyes open). One-shot; pairs with `target_lock`."""
from ..primitives import smoothstep
from ..spec import Vibe
from .target_lock import _aim_eyes, _corners   # release keeps lock's one-eyed face + frame

_REL = 0.4                                    # how long the break-lock takes


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    t = now.t
    _aim_eyes(d)                                  # still squinting as the lock drops
    _corners(d, 1.0 - smoothstep(min(1.0, t / _REL)))   # brackets fly back out to the corners


def _expired(now):
    return now.t >= _REL


VIBE = Vibe("target_release", mood="neutral", overlay=_overlay, expired=_expired)
