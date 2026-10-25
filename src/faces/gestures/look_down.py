"""Glance down and hold, then return."""
from ..engine import look
from ..spec import Gesture

GESTURE = Gesture("look_down", dur=1.2, motion=look(0, 10))
