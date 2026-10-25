"""Persistent data HUDs -- a looping Action that shows information, not emotion. Mechanically
these ARE actions (see spec.Widget); they live here so the menu/showcase can group opt-in info
displays apart from task statuses. Add one: drop `<name>.py` exposing `WIDGET = Widget(...)`,
then slot its name into the curated order below."""
from .._registry import load

# -- curated order; time/notice first, then media, then device telemetry --
_ORDER = (
    "clock", "weather", "now_playing", "notif_badge",
    "battery_gauge",                                             # charge level
    "cc_usage",                                                  # Claude Code 5h/weekly token limits
    "sponsor",                                                   # GitHub Sponsors QR + kawaii face
)

WIDGETS = load(__name__, _ORDER, "WIDGET")   # name -> Widget(=Action), curated order
