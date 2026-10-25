"""Both eyes blink twice."""
from ..spec import Gesture

GESTURE = Gesture("double_blink", dur=0.44, blink=({"left", "right"}, 2))
