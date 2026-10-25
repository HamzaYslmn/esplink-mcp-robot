"""Looping task statuses -- what Pip is *doing*, driven by the Claude Code hooks. Add one: drop
`<name>.py` here exposing `ACTION = Action(...)`, then slot its name into the curated order below.
('idle' isn't an entry -- it's the resting stop: set_activity('idle'), or any unknown name, just
stops whatever's looping.) Pure eye-candy loops live in vibes/, live-data HUDs in widgets/."""
from .._registry import load

# -- curated order; work, then links/holding, then a break --
_ORDER = (
    "thinking", "scanning", "searching", "processing",           # heads-down work
    "working", "editing", "debugging", "building", "testing", "deploying",
    "connecting", "ping_pong", "listening", "waiting",           # links & holding pattern
    "glitch",                                                     # a crash / corruption fit
)

ACTIONS = load(__name__, _ORDER, "ACTION")   # name -> Action, curated order (errors on a stray file)
