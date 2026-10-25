"""Held expressions. Add one: drop `<name>.py` here exposing `MOOD = Mood(...)`, then slot
its name into the curated order below (the order drives the menu, the showcase, the LLM enum)."""
from .._registry import load

# -- curated display order, grouped by feel --
_ORDER = (
    # system
    "alert", "attentive", "standby",
    # positive / warm
    "happy", "lovely", "kawaii", "cat", "awe", "cool",
    # focus / calm
    "focused", "wired", "chill",
    # sad / anxious / low
    "sad", "gloomy", "worried", "nervous", "despair", "scared", "tired", "sleepy",
    # angry / wary
    "angry", "furious", "devil", "suspicious", "skeptical",
    # dazed / goofy / off
    "surprised", "dumb", "confused", "disoriented", "bored", "dead",
    # baseline
    "neutral",
)

MOODS = load(__name__, _ORDER, "MOOD")   # name -> Mood, curated order (errors on a stray file)
