"""Glance up and hold, then return."""
from ..primitives import look
from ..spec import Gesture

GESTURE = Gesture("look_up", dur=1.2, motion=look(0, -10))
