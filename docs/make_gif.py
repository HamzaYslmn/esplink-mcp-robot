"""Render Pip's faces headlessly off the real eye engine (no hardware).

    uv run docs/make_gif.py            # writes docs/pip-eyes.gif (every face, labelled)
    uv run docs/make_gif.py zen        # writes docs/zen_preview.png (one face, 5 frames)

No args -> the full showcase GIF. A face name (mood / gesture / activity) ->
a 5-frame contact sheet for eyeballing that one face during development.
Both drive the engine off a virtual clock -- no thread, no sleeping -- so they
render as fast as the CPU allows.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from faces import (  # noqa: E402
    ACTIONS, GESTURES, LOOPING, MOODS, PLAYABLE, REACTIONS, VIBES, WIDGETS, EyeEngine)

W, H = 128, 64
SCALE = 3          # pixel zoom for the eyes
BAR = 28           # caption strip height (px, unscaled)
FPS = 14           # GIF frame rate == engine step rate (one step per output frame)
MOOD_SEC = 0.9     # dwell per mood
ACT_SEC = 1.6      # dwell per activity
GEST_PAD = 0.4     # extra time after a gesture's own duration
SETTLE = 0.4       # settle to a plain face before a gesture
LEAD = 0.3         # lead-in before a mood/activity so its swap-blink finishes
OUT = ROOT / "docs" / "pip-eyes.gif"

PREVIEW_SCALE = 2  # pixel zoom for a preview frame
PREVIEW_FRACS = (0.1, 0.3, 0.5, 0.7, 0.9)   # where in a face's window each preview frame is grabbed


class Driver:
    """A virtual clock + the engine, stepped by hand at FPS -- no thread, no sleep."""

    def __init__(self):
        self.t = 0.0
        self.eyes = EyeEngine(lambda _img: None, fps=FPS, clock=lambda: self.t)
        self.eyes.reset_timers(self.t)
        self.eyes.set_activity("idle")
        self.eyes.set_mood("neutral")

    def run(self, seconds):
        """Advance `seconds` of animation one FPS step at a time, returning the frames."""
        out = []
        for _ in range(max(1, round(seconds * FPS))):
            self.t += 1.0 / FPS
            out.append(self.eyes.step(self.t).copy())
        return out

    def lead_in(self, kind, name):
        """Put the engine into the face, advancing through its settle; return its window length."""
        if kind == "gesture":
            self.eyes.set_mood("neutral")
            self.run(SETTLE)                 # settle to a plain face, then fire the one-shot
            self.eyes.play_gesture(name)
            return PLAYABLE[name].dur
        if kind == "activity":
            self.eyes.set_activity(name)
            self.run(LEAD)
            return ACT_SEC
        self.eyes.set_mood(name)
        self.run(LEAD)
        return MOOD_SEC + LEAD


def _load_font(size=16):
    for name in ("arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _kind(name):
    """Which mechanic a face name plays as (None if unknown). Reactions play as a gesture,
    widgets as an activity -- the two pooled dispatch layers."""
    if name in MOODS:
        return "mood"
    if name in PLAYABLE:
        return "gesture"
    if name in LOOPING:
        return "activity"
    return None


# --------------------------------------------------------------- showcase GIF
def _script():
    """The ordered (caption, dwell, kind, name) walk the showcase records."""
    yield "Pip", 1.0, None, None
    for m in MOODS:
        yield f"mood: {m}", MOOD_SEC, "mood", m
    for g in GESTURES:
        yield f"gesture: {g}", max(0.8, PLAYABLE[g].dur + GEST_PAD), "gesture", g
    for r in REACTIONS:
        yield f"reaction: {r}", max(0.8, PLAYABLE[r].dur + GEST_PAD), "gesture", r
    for a in ACTIONS:
        yield f"activity: {a}", ACT_SEC, "activity", a
    for v in VIBES:
        yield f"vibe: {v}", ACT_SEC, "activity", v
    for w in WIDGETS:
        yield f"widget: {w}", ACT_SEC, "activity", w


def _compose(eye, caption, font):
    big = eye.convert("L").resize((W * SCALE, H * SCALE), Image.NEAREST)
    canvas = Image.new("L", (W * SCALE, H * SCALE + BAR), 0)
    canvas.paste(big, (0, 0))
    d = ImageDraw.Draw(canvas)
    tw = d.textlength(caption, font=font)
    d.text(((W * SCALE - tw) / 2, H * SCALE + (BAR - 16) / 2), caption, fill=255, font=font)
    return canvas


def main():
    drv = Driver()
    frames = []                                  # (eye image, caption)
    for caption, dwell, kind, name in _script():
        if kind:
            drv.lead_in(kind, name)
        frames += [(f, caption) for f in drv.run(dwell)]

    print(f"composing {len(frames)} frames...")
    font = _load_font()
    imgs = [_compose(eye, cap, font) for eye, cap in frames]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    imgs[0].save(OUT, save_all=True, append_images=imgs[1:], optimize=True,
                 duration=int(1000 / FPS), loop=0)
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(imgs)} frames, {kb:.0f} KB)")


# ----------------------------------------------------------- single-face preview
def _compose_preview(frames, name, kind, font, small):
    """Stack the frames into one labelled filmstrip (name header + per-frame index)."""
    fw, fh, head, gap = W * PREVIEW_SCALE, H * PREVIEW_SCALE, 22, 4
    canvas = Image.new("L", (fw, head + len(frames) * (fh + gap)), 0)
    d = ImageDraw.Draw(canvas)
    d.text((6, 3), f"{name}  ({kind})", fill=255, font=font)
    for i, f in enumerate(frames):
        y = head + i * (fh + gap)
        canvas.paste(f.convert("L").resize((fw, fh), Image.NEAREST), (0, y))
        d.text((4, y + 2), f"n={i}", fill=255, font=small)
    return canvas


def preview(name):
    name = name.lower()
    kind = _kind(name)
    if not kind:
        print(f"unknown face: {name!r}; try one of: {' '.join([*MOODS, *PLAYABLE, *LOOPING])}",
              file=sys.stderr)
        return 2

    drv = Driver()
    drv.run(LEAD)                                # let the opening neutral idle settle
    window = drv.lead_in(kind, name)
    seq = drv.run(window)
    frames = [seq[min(len(seq) - 1, round(frac * len(seq)))] for frac in PREVIEW_FRACS]

    out = ROOT / "docs" / f"{name}_preview.png"
    _compose_preview(frames, name, kind, _load_font(), _load_font(12)).save(out, optimize=True)
    print(f"wrote {out.relative_to(ROOT)}  ({len(frames)} frames)")
    return 0


if __name__ == "__main__":
    sys.exit(preview(sys.argv[1]) if len(sys.argv) > 1 else main())
