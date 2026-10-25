"""Demo menu (`esplink-buddy demo`) -- play any face live, or save one as a GIF
(`esplink-buddy gif <name|number>`, or `g<name|number>` inside the menu)."""
from __future__ import annotations

import time

from faces import ACTIONS, GESTURES, MOODS, REACTIONS, VIBES, WIDGETS

# One column per folder; the menu numbers run through them in this order.
_COLUMNS = (("MOODS", MOODS), ("GESTURES", GESTURES), ("REACTIONS", REACTIONS),
            ("ACTIONS", ACTIONS), ("VIBES", VIBES), ("WIDGETS", WIDGETS))
ITEMS = [n for _, reg in _COLUMNS for n in reg]      # flat list the menu numbers index into


def _find(token):
    """A menu number or a face name -> the face name (None if neither)."""
    if token.isdigit():
        return ITEMS[int(token) - 1] if 1 <= int(token) <= len(ITEMS) else None
    return token if token in ITEMS else None


def save_gif(token):
    """Render a 30s GIF of a face (name or menu number) into the cwd; returns the path, or None."""
    name = _find(str(token).lower())
    if not name:
        print(f"unknown face {token!r} -- use a name or number from `esplink-buddy demo`")
        return None
    from faces.record import record_gif
    print(f"-> rendering 30s GIF of {name} ...")
    out = record_gif(name)
    print(f"wrote {out}")
    return out


def _show_menu():
    w = max(map(len, ITEMS)) + 4                       # "NN. " prefix + widest name
    cols, off = [], 0
    for title, reg in _COLUMNS:                        # each column numbers on from the last
        cols.append((title, [f"{off + i:>2}. {n:<{w - 4}}" for i, n in enumerate(reg, 1)]))
        off += len(reg)
    rule = "=" * (w * len(cols) + 3 * (len(cols) - 1))
    print(f"\n  {rule}\n   Pip demo menu\n  {rule}")
    print("  " + " | ".join(f"{t:<{w}}" for t, _ in cols))
    print("  " + "-+-".join("-" * w for _ in cols))
    for r in range(max(len(c) for _, c in cols)):
        print("  " + " | ".join(c[r] if r < len(c) else " " * w for _, c in cols).rstrip(" |"))
    print(f"  {rule}\n  a = play all (2s each)    gNN = save 30s GIF    q = quit    (number or name)")


def _play(eyes, name):
    print(f"-> {name}")
    if name in MOODS:
        eyes.set_activity("idle")                      # a mood alone, no loop on top
    elif name not in GESTURES and name not in REACTIONS:
        eyes.set_mood("neutral")                       # a loop on a plain face
    eyes.show(name)


def demo(robot):
    """Interactive menu: pick an emotion, gesture or activity to play."""
    eyes = robot.eyes
    _show_menu()
    while True:
        try:
            choice = input("demo> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if choice in {"q", "quit", "exit"}:
            break
        if not choice:
            _show_menu()
        elif choice == "a":
            for name in ITEMS:
                _play(eyes, name)
                time.sleep(2.0)
            eyes.set_activity("idle")
        elif choice[0] == "g" and _find(choice[1:]):   # gzen / g13 -> save a GIF
            save_gif(choice[1:])
        elif name := _find(choice):
            _play(eyes, name)
        else:
            print(f"unknown: {choice!r} (enter a number, name, 'a', or 'q')")
    eyes.set_activity("idle")
