"""Glance left; the near eye parallax-swells."""
from ..engine import look
from ..spec import Gesture

GESTURE = Gesture("look_left", dur=1.2, motion=look(-8, 0, -0.2))
