"""Decorative looping animations -- a vibe just *plays out*: it shows no task status and no live
data, it's pure scenery (a campfire, the matrix rain, pixel-sand decay). Mechanically these ARE
actions (see spec.Vibe); they live here so the menu/showcase can group eye-candy apart from
real activities. Add one: drop `<name>.py` exposing `VIBE = Vibe(...)`, then slot its name into
the curated order below."""
from .._registry import load

# -- curated order; screen/glitch fx, then scanners/boot, then machine work, games, ambient --
_ORDER = (
    "matrix", "warp", "recording", "ascii_morph", "pixel_decay", "emp_pulse",   # screen / glitch fx
    "cylon", "blackhole", "supernova", "solarflare",   # cosmic
    "boot_draw", "barcode_scan", "target_lock", "target_release", "thermal_scan",  # scanners / boot
    "defrag_blocks", "energy_blast", "nuke", "game_of_life", "tesseract", "quantum",   # machine work
    "jackpot", "dice_roll", "snake",                                   # games
    "campfire", "snore", "smoking", "zen", "overheated",              # cozy / ambient
)

VIBES = load(__name__, _ORDER, "VIBE")   # name -> Vibe(=Action), curated order (errors on a stray file)
