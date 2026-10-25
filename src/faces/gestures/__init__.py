"""Self-initiated one-shot moves -- idle glances Pip makes on its own, not aimed at anyone. Add
one: drop `<name>.py` here exposing `GESTURE = Gesture(...)`, then slot its name into the curated
order below. A gesture is either a `blink` (lid-only) or a `motion`. (Reflexes and social replies
to the user live in reactions/, not here.)"""
from .._registry import load

# -- curated order; blinks first, then enveloped motions --
_ORDER = (
    # blinks (lid-only)
    "blink", "double_blink", "wink_left", "wink_right",
    # gaze glances + directional blinks + sweeps
    "look_left", "look_right", "look_up", "look_down", "blink_down", "blink_up",
    "scan", "scan_sweep",
)

GESTURES = load(__name__, _ORDER, "GESTURE")   # name -> Gesture, curated order (errors on a stray file)
