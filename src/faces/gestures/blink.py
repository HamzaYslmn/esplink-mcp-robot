"""Both eyes blink once."""
from ..spec import Gesture

GESTURE = Gesture("blink", dur=0.20, blink=({"left", "right"}, 1))
