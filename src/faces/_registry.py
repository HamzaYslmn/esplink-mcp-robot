"""Build a folder's ordered {name: effect} registry from its curated _ORDER tuple, and fail loud
if a sibling effect file was added but left out of the order (the easy mistake to make)."""
from importlib import import_module
from pathlib import Path


def load(pkg, order, attr):
    """pkg = the folder package __name__; order = the curated name tuple; attr = MOOD/GESTURE/ACTION."""
    reg = {n: getattr(import_module(f"{pkg}.{n}"), attr) for n in order}
    folder = Path(import_module(pkg).__file__).parent
    stray = {p.stem for p in folder.glob("*.py") if not p.stem.startswith("_")} - set(order)
    if stray:
        raise ImportError(f"{pkg}: effect file(s) missing from _ORDER: {sorted(stray)}")
    return reg
