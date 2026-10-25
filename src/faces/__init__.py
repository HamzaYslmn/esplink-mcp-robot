"""Procedural robot eyes for a 128x64 OLED (PIL).

Each effect is ONE self-contained file in a folder, named by what it IS:
  moods/     a held expression       (size + lid paint + decor)   -> MOODS    {name: Mood}
  gestures/  a self-initiated one-shot (idle blink or glance)     -> GESTURES {name: Gesture}
  reactions/ a one-shot in response    (reflex, or reply to user) -> REACTIONS{name: Reaction}
  actions/   a looping task status   (what Pip's doing)            -> ACTIONS  {name: Action}
  vibes/     a looping decoration    (pure eye-candy, no meaning)  -> VIBES    {name: Vibe}
  widgets/   a looping data HUD      (an Action that shows info)   -> WIDGETS  {name: Widget}
Reactions reuse the gesture mechanic; vibes and widgets the action mechanic (see spec.py), so the
engine dispatches just two pooled registries: PLAYABLE (one-shots) and LOOPING (loops).
Each registry is an ordered dict (curated in its folder's __init__). Shared bits: spec.py
(the schema), primitives.py (pure math/draw -- ease/smoothstep/lid_openness/rounded_rect/rand/flip/
frame), painters.py (lid carvers + the twinkle motif), engine.py (the renderer + the `look`
glance helper). Reach for those shared helpers rather than re-rolling them per file: e.g. all
pseudo-randomness goes through one `rand()`. Single-use helpers live in their own effect file.
Add an effect by dropping a file in a folder + one line in its __init__ order list -- see
spec.py. The whole package is self-contained (relative imports only), so it drops into any app:
copy the faces/ folder, `pip install pillow`, and drive EyeEngine."""
from .actions import ACTIONS
from .gestures import GESTURES
from .moods import MOODS
from .reactions import REACTIONS
from .vibes import VIBES
from .widgets import WIDGETS

# Two dispatch pools the engine plays from: reactions are one-shots like gestures; vibes and
# widgets are loops like actions. Keep the six registries too, so menus/showcase group by folder.
PLAYABLE = {**GESTURES, **REACTIONS}        # play_gesture() accepts any of these
LOOPING = {**ACTIONS, **VIBES, **WIDGETS}   # set_activity() accepts any of these

from .engine import EyeEngine          # imported last: it reads PLAYABLE/LOOPING above at init

__all__ = ["EyeEngine", "MOODS", "GESTURES", "REACTIONS", "ACTIONS", "VIBES", "WIDGETS",
           "PLAYABLE", "LOOPING"]
