"""Processing -- Pip's eyes as a computer's front panel, showing the machine actually running. Each eye
is a bezel round a 4x4 grid of lamps; the two together are one 8-bit-wide panel of registers:

  row 0   PC      the program counter: stepping through the code, jumping on branches
  row 1   ADDR    the address bus: following the PC, off to data on loads and stores
  row 2   DATA    the data bus: whatever's on it this instruction
  row 3   STATUS  RUN, FETCH, MEM, WAIT -- and the accumulator's low four bits

The machine runs a random string of workloads: plain code (steady stepping, branches), a tight loop
(the PC cycling a few addresses while the address walks through an array), heavy crunching (the
clock flat out), a block copy (addresses marching through source and destination), waiting on I/O
(the PC parked polling, WAIT lit, Pip glancing off for it), and now and then a fault (everything
freezes, RUN drops, Pip jolts -- then it carries on). Lamps glow a beat after they go out, like
real filament lamps.

Self-check: `cd src && uv run python -m faces.actions.processing`."""
import math
from functools import cache

from ..primitives import frame, rand, smoothstep
from ..spec import Action

_JOB = 9.0                     # s per stretch (then a fresh random string)
_KINDS = (                     # (workload, weight, (shortest, longest) s, instructions per s)
    ("run", 0.34, (1.6, 2.6), 14), ("loop", 0.2, (1.2, 2.0), 18), ("crunch", 0.18, (1.0, 1.6), 30),
    ("copy", 0.13, (0.8, 1.2), 24), ("wait", 0.1, (0.8, 1.4), 3), ("fault", 0.05, (0.9, 0.9), 0),
)
_RATE = {k: hz for k, _, _, hz in _KINDS}
_COLS, _ROWS = 4, 4            # lamps per eye
_BEZEL = 2                     # px of lit eye outline round the panel
_PITCH = 6.6                   # px between lamps


# -- the plan ------------------------------------------------------------------------------------------
@cache
def _plan(s):
    """A random string of workloads filling _JOB: ((kind, seconds), ...); never the same twice running,
    never opening on a fault."""
    phases, t, last, i = [], 0.0, "fault", 0
    while t < _JOB - 0.8:
        i += 1
        options = [(k, w) for k, w, _, _ in _KINDS if k != last]
        r, kind = rand(s, i, 2) * sum(w for _, w in options), options[0][0]
        for k, w in options:
            if r < w:
                kind = k
                break
            r -= w
        lo, hi = next(span for k, _, span, _ in _KINDS if k == kind)
        dur = lo + rand(s, i, 3) * (hi - lo)
        phases.append((kind, dur))
        t, last = t + dur, kind
    return tuple(phases[:-1]) + ((phases[-1][0], phases[-1][1] - (t - _JOB)),)


def _phase(now):
    """(kind, seconds into it, its length, its seed) of the workload running now."""
    T, seed = getattr(now, "t", now), getattr(now, "seed", 0)
    s = int(rand(seed, T // _JOB) * 1e6)
    t, before = T % _JOB, None
    for i, (kind, dur) in enumerate(_plan(s)):
        if t < dur:
            return kind, t, dur, s * 31 + i, before
        t -= dur
        before = (kind, dur, s * 31 + i)
    kind, dur = _plan(s)[-1]
    return kind, dur, dur, s * 31 + len(_plan(s)) - 1, before


# -- the machine ---------------------------------------------------------------------------------------
def _registers(kind, n, s):
    """(pc, addr, data, status) bytes after instruction n of a workload seeded s."""
    pc, acc = int(rand(s, 1) * 200), int(rand(s, 2) * 16)
    array, src, dst = int(rand(s, 3) * 256), int(rand(s, 4) * 256), int(rand(s, 5) * 256)
    body = 3 + int(rand(s, 6) * 4)                          # a tight loop's length
    addr = data = mem = 0
    for i in range(n + 1):
        data = int(rand(s, i, 7) * 256)
        if kind == "loop":                                  # cycle the body, walking an array
            pc_i, mem = pc + i % body, i % body == 1
            addr = (array + i // body) % 256 if mem else pc_i
        elif kind == "copy":                                # load from src, store to dst, step on
            pc_i, mem = pc + i % 2, True
            addr = (src if i % 2 == 0 else dst) + i // 2
            data = int(rand(s, i // 2, 7) * 256)            # the same byte goes in and out
        elif kind == "wait":                                # parked polling the device
            pc_i, mem, addr, data = pc + i % 2, True, 0xF0 + i % 2, 0
        else:                                               # straight code: step, branch, load/store
            pc += 1
            if rand(s, i, 8) < (0.08 if kind == "crunch" else 0.13):
                pc = int(rand(s, i, 9) * 256)
            pc_i, mem = pc, rand(s, i, 10) < 0.35
            addr = int(rand(s, i, 11) * 256) if mem else pc_i
        acc = (acc * 5 + data) % 16
    status = (kind != "fault") << 7 | (n % 2) << 6 | mem << 5 | (kind == "wait") << 4 | acc
    return pc_i % 256, addr % 256, data, status


def _panel(now):
    """The lamps now and a beat ago: (lit rows, lit rows one instruction back), each 4 bytes."""
    kind, u, dur, s, before = _phase(now)
    if kind == "fault":                                     # frozen where the last workload stopped
        if before is None:
            return (0, 0, 0, 0), (0, 0, 0, 0)
        bk, bdur, bs = before
        regs = list(_registers(bk, int(bdur * _RATE[bk]), bs))
        regs[3] = regs[3] & 0x7F | (int(u * 6) % 2) << 4   # RUN out; the WAIT lamp blinks the alarm
        return tuple(regs), tuple(regs)
    n = int(u * _RATE[kind])
    return _registers(kind, n, s), _registers(kind, max(0, n - 1), s)


def _eyes(d, x, y, w, h, right, now):
    """Each eye is half the panel: a lit bezel round a dark face; lamps lit, just-out (still glowing),
    or dark (just a glint)."""
    b = _BEZEL
    if frame(d) is None or h < 2 * b + 3 or w < 2 * b + 3:
        return                                              # mid-blink sliver: leave it plain
    d.rounded_rectangle([x + b, y + b, x + w - 1 - b, y + h - 1 - b], radius=max(1, min(w, h) / 3 - b), fill=0)
    rows = max(0, min(_ROWS, round((h - 2 * b - 4) / _PITCH)))   # a blink squeezes rows out
    if not rows:
        return
    lit, was = _panel(now)
    gx, gy = (w - (_COLS - 1) * _PITCH) / 2, (h - (rows - 1) * _PITCH) / 2
    first = (_ROWS - rows) // 2
    for r in range(rows):
        for c in range(_COLS):
            bit = 1 << (7 - c - (_COLS if right else 0))
            cx, cy = x + gx + c * _PITCH, y + gy + r * _PITCH
            k = 2.5 if lit[r + first] & bit else 1.5 if was[r + first] & bit else 0
            if k:
                d.ellipse([cx - k, cy - k, cx + k, cy + k], fill=1)
            else:
                d.point((round(cx), round(cy)), fill=1)


def _pose(now):   # eyes on the work; tremble when crunching, glance off for I/O, jolt on a fault
    kind, u, dur, _, _ = _phase(now)
    drift = math.sin(now * 0.7) * 1.2, math.sin(now * 0.5) * 0.8
    k = smoothstep(min(u / 0.25, 1.0, (dur - u) / 0.25))
    if kind == "crunch":
        return drift[0] + math.sin(now * 37) * 0.6 * k, drift[1] + math.cos(now * 29) * 0.4 * k, 1.0
    if kind == "wait":
        return -6 * k, -2 * k, 1.0
    if kind == "fault":
        j = math.exp(-u * 4)
        return 2.5 * math.sin(u * 32) * j, -1.5 * j, 1.0 + 0.06 * j
    return drift[0], drift[1], 1.0


ACTION = Action("processing", mood="neutral", pose=_pose, eyes=_eyes)


if __name__ == "__main__":
    seen = set()
    for s in range(300):
        plan = _plan(s)
        seen |= {k for k, _ in plan}
        assert abs(sum(dur for _, dur in plan) - _JOB) < 1e-9 and all(d > 0 for _, d in plan), "fills its slot"
        assert all(a[0] != b[0] for a, b in zip(plan, plan[1:])) and plan[0][0] != "fault", "varied, no cold fault"
    assert seen == {k for k, *_ in _KINDS}, f"every workload comes up: {seen}"
    pcs = [_registers("run", n, 5)[0] for n in range(60)]
    steps = sum(b == (a + 1) % 256 for a, b in zip(pcs, pcs[1:]))
    assert 40 < steps < 59, "straight code mostly steps, sometimes branches"
    loop = [_registers("loop", n, 5)[0] for n in range(30)]
    assert len(set(loop)) <= 6, "a tight loop cycles a few addresses"
    copy = [_registers("copy", n, 5) for n in range(8)]
    assert all(copy[i][2] == copy[i + 1][2] for i in range(0, 8, 2)), "a copy moves the same byte in and out"
    assert _registers("wait", 4, 5)[3] & 0x10 and not _registers("run", 4, 5)[3] & 0x10, "WAIT lights only when waiting"
    print("processing ok")
