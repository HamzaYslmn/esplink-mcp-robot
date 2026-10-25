"""Step the gaze left->right then down a line -- scanning (no overlay prop)."""
from ..spec import Action


def _pose(now):   # step left->right then down a line, settling each stop
    line = now * 1.0
    return (int(line % 1.0 * 4) / 3 * 2 - 1) * 13, (int(line) % 3 - 1) * 5, 1.0


ACTION = Action("scanning", mood="attentive", pose=_pose)
