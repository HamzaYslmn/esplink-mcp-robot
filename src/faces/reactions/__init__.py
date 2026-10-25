"""One-shot moves fired *in response to the world or the user* -- reflexes a sensor/event jolts
out of Pip, and social replies that answer the user (nod/refuse/acknowledge) -- not the idle
glances Pip makes on its own (those are gestures/). Mechanically these ARE gestures (see
spec.Reaction); they live here so the menu/showcase/LLM can group responses apart from
self-initiated moves. Add one: drop `<name>.py` exposing `REACTION = Reaction(...)`, then slot its
name into the curated order below."""
from .._registry import load

# -- curated order; social replies, then expressive reflexes, then event/sensor-fired --
_ORDER = (
    # social replies to the user: affirm / deny / acknowledge
    "nod", "refuse", "acknowledge",
    "laugh", "excited", "pop", "shiver", "roll", "squint", "cross_eyes",
)

REACTIONS = load(__name__, _ORDER, "REACTION")   # name -> Reaction(=Gesture), curated order
