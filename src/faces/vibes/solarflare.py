"""Solar flare -- a coronal mass ejection hits Pip and fries it, in a long staged sequence:

  calm     quiet scared eyes; a glow brews on the horizon
  wave     a viscous wall of plasma oozes across (advection + diffusion -- a real transport flow),
           writhing and merging like goo, throwing lightning precursor tendrils ahead as it nears
  surge    impact -- overvoltage floods the panel, sparks crawl in from the edges
  short    the supply collapses on a real RC discharge  V(t)=V_surge*e^(-t/tau);  as the logic
           voltage sags the display browns out in stages -- bit errors climb, sync tears the rows,
           the rail stutters (failed brown-out recoveries), then it dies
  dead     black; a blinking POWER-LOSS / SYSTEM-FAILURE / error-code screen with a flatline. It
           sits here erroring; every 5s it attempts a boot -- 40% it wakes for real (-> reboot),
           else the boot glitches out (-> wakefail) and it drops back to the error screen
  wakefail a failed wake: the raster claws partway up, then tears apart in a glitch and collapses
           back to dead -- Pip keeps trying (error -> attempt -> glitch -> error) until a roll boots it
  reboot   a real power-on sequence: the cap recharges  V(t)=1-e^(-t/tau);  backlight flicker ->
           raster scanline fill -> a BOOT progress bar -> the eyes wipe back in -> glitch settles

Triggered by real space weather, replayed one day behind: we can't watch the live feed in real
time, so on open `watch(trigger)` makes ONE request for *yesterday's* NOAA flare events, keeps the
M+ peaks in memory as a time-of-day schedule, and re-enacts each at the same wall-clock (UTC) time
today. Just one fetch per 24h -- refreshed when the day rolls over -- yet Pip lives the Sun's storms
in real time, a day late. Each flare fires `trigger()` once -> the solarflare face; the effect then
plays through once and self-ends.
Self-check: `cd src && uv run python -m faces.vibes.solarflare`."""
import datetime
import json
import math
import threading
import time
import urllib.request

import numpy as np
from PIL import ImageFont

if __name__ == "__main__" and not __package__:    # run the file directly: relative imports need a
    import pathlib                                 # package, so put src/ on the path and name ourselves
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))
    __package__ = "faces.vibes"

from ..primitives import frame, rand, smoothstep
from ..spec import Vibe

_T_CALM, _T_WAVE, _T_SURGE = 2.0, 2.8, 0.5    # quiet; the shock crawls in; the overvoltage strike
_T_DEAD, _T_REBOOT = 3.2, 3.4                  # dark with the error; the boot
_WAVE_C = (70.0 + 14.0) / _T_WAVE              # front speed (px/s) -- reaches the eyes as the wave ends
_V_SURGE = 1.5                                 # overvoltage spike (x nominal)
_TAU_DIS, _TAU_CHG = 2.3, 1.0                  # RC discharge / recharge time constants (s)
_V_TH, _V_ON = 0.45, 0.55                      # logic dies below _V_TH; raster returns above _V_ON
_T_ROLL, _P_REBOOT = 5.0, 0.4                  # while dead: every 5s a boot attempt -- 40% wakes for real
_T_WAKEFAIL = 1.4                              # a failed boot: raster tries to lock, glitches out, drops back to dead

_BAYER = [[(v + 0.5) / 16.0 for v in row] for row in (
    (0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))]
_COLS = np.arange(128)
_BAYER_TILE = np.tile(np.array(_BAYER), (16, 32))   # 4x4 dither -> full 64x128, for the vectorized plasma
_YS = np.arange(64)
_ENV = np.sin(np.pi * _YS / 63)                      # bright-cored vertical bulge of the plasma wall
_VISC = 9.0                                          # diffusion rate -- the gooeyness (higher = blobbier, mergier)
_TAU_TAIL = 0.45                                     # trailing plasma bleeds away over ~0.45s (a thick tail, not a fill)
try:
    _FONT = ImageFont.load_default(size=11)
    _FONT_S = ImageFont.load_default(size=8)
except TypeError:
    _FONT = _FONT_S = ImageFont.load_default()
_S = {"on": False, "last": None}


def _put(d, x, y, v):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < 128 and 0 <= y < 64 and v > _BAYER[y & 3][x & 3]:
        d.point((x, y), fill=1)


def _bolt(d, x0, y0, x1, y1, seed, jag=4.0):
    """A jagged lightning segment from (x0,y0)->(x1,y1) by midpoint displacement."""
    pts = [(x0, y0), (x1, y1)]
    for it in range(4):
        nxt = []
        for i in range(len(pts) - 1):
            ax, ay = pts[i]
            bx, by = pts[i + 1]
            mx, my = (ax + bx) / 2, (ay + by) / 2
            r = (np.sin((seed + i + it * 7) * 12.9898) * 43758.5453) % 1.0 - 0.5
            nx, ny = -(by - ay), (bx - ax)
            nl = math.hypot(nx, ny) + 1e-6
            nxt += [(ax, ay), (mx + nx / nl * r * jag, my + ny / nl * r * jag)]
        nxt.append(pts[-1])
        pts = nxt
    for i in range(len(pts) - 1):
        d.line([pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]], fill=1)


def _front_x(pt):
    return -14.0 + _WAVE_C * pt


def _v_discharge(pt):
    return _V_SURGE * math.exp(-pt / _TAU_DIS)


def _v_recharge(pt):
    return 1.0 - math.exp(-pt / _TAU_CHG)


def _ber(v):
    return max(0.0, 1.0 - v) * 0.28


def _reset(now):
    _S.update(on=True, last=now, phase="calm", pt=0.0, fluid=None, carry=0.0, dt=1 / 30.0)


def _step(now):
    s = _S
    if not s["on"] or s["last"] is None or now < s["last"] or now - s["last"] > 0.5:
        _reset(now)
        return
    dt = now - s["last"]
    s["last"] = now
    s["dt"] = dt
    s["pt"] += dt
    ph = s["phase"]
    nxt = {"calm": ("wave", _T_CALM), "wave": ("surge", _T_WAVE), "surge": ("short", _T_SURGE)}
    if ph == "short":
        if _v_discharge(s["pt"]) < _V_TH:
            s["phase"], s["pt"], s["dead_t0"], s["attempt"] = "dead", 0.0, now, 0   # rail's gone -> error screen
    elif ph == "dead":                                        # sit on the error, then attempt a boot every _T_ROLL s
        if s["pt"] >= _T_ROLL:
            s["attempt"] += 1                                 # an independent roll per attempt
            woke = rand(s["dead_t0"] + s["attempt"] * 7.31) < _P_REBOOT
            s["phase"], s["pt"] = ("reboot" if woke else "wakefail"), 0.0   # 40% wakes; else it'll glitch out
    elif ph == "wakefail":                                    # tried to boot, glitched -> back to the error screen
        if s["pt"] >= _T_WAKEFAIL:
            s["phase"], s["pt"] = "dead", 0.0
    elif ph == "reboot":
        if s["pt"] >= _T_REBOOT:
            s["phase"] = "done"                               # played once -> _expired ends it
    elif ph in nxt and s["pt"] >= nxt[ph][1]:
        s["phase"], s["pt"] = nxt[ph][0], 0.0
        if s["phase"] == "wave":
            s["fluid"] = None                                  # fresh plasma field each run


# ---------------------------------------------------------------- drawing
def _arr(img):
    return np.array(img, dtype=bool)


def _blit(img, a):
    img.frombytes(np.packbits(a, axis=1).tobytes())


def _draw_calm(d, s):
    glow = smoothstep(s["pt"] / _T_CALM)                       # the flare brightens the horizon
    for y in range(0, 64, 2):
        _put(d, 1, y, glow * 0.8)
        _put(d, 3, y, glow * 0.45)
        _put(d, 5, y, glow * 0.2)


def _advance_fluid(s, now):
    """One step of a real plasma transport: inject a turbulent wall at the left, advect it right at
    the front speed, diffuse it (viscosity -> the goo), bleed the tail. Emergent, not a drawn curve."""
    F = s.get("fluid")
    if F is None:
        F = np.zeros((64, 128))
    dt = min(0.1, s.get("dt", 1 / 30.0))                       # cap the first big frame after a phase switch
    carry = s.get("carry", 0.0) + _WAVE_C * dt                 # advect right, sub-pixel carried between frames
    n = int(carry)
    s["carry"] = carry - n
    if n:
        F = np.roll(F, n, axis=1)
        F[:, :n] = 0.0                                         # outflow at the right, clean source at the left
    a = min(1.0, _VISC * dt)                                   # viscous diffusion: a 3-tap separable blur, mixed in
    h = (np.roll(F, 1, 1) + 2 * F + np.roll(F, -1, 1)) * 0.25
    h = (np.roll(h, 1, 0) + 2 * h + np.roll(h, -1, 0)) * 0.25
    F = (1.0 - a) * F + a * h
    F *= math.exp(-dt / _TAU_TAIL)                             # the trailing plasma bleeds to a gooey tail
    np.random.seed(int(now * 30) % 99991)
    fil = 0.55 + 0.45 * np.sin(_YS * 0.5 + now * 7)            # filaments writhe down the wall
    src = (0.7 + 1.1 * _ENV) * fil * (0.7 + 0.6 * np.random.random(64))
    F[:, :3] = np.maximum(F[:, :3], src[:, None])              # keep feeding the bright-cored wall
    s["fluid"] = F
    return F


def _draw_wave(d, s, now):
    F = _advance_fluid(s, now)
    img = frame(d)
    if img is not None:
        a = _arr(img)
        a |= (F > _BAYER_TILE)                                 # dither the gooey plasma over the live eyes
        _blit(img, a)
    u = s["pt"] / _T_WAVE
    if u > 0.55:                                               # precursor tendrils reach toward Pip
        fx = _front_x(s["pt"])
        for k in range(3):
            ty = 20 + k * 12
            _bolt(d, fx, ty, fx + (64 - fx) * (u - 0.55) / 0.45, ty + (k - 1) * 6, k + int(s["pt"] * 8), 5)


def _draw_surge(d, s, now):
    img = frame(d)
    if img is None:
        return
    np.random.seed(int(now * 30) % 99991)
    a = _arr(img)
    f = 1.0 - s["pt"] / _T_SURGE
    a = a | (np.random.random((64, 128)) < 0.6 * f)            # overvoltage floods every cell
    _blit(img, a)
    for k in range(4):                                         # sparks crawling in from the edges
        ex = 0 if k % 2 else 127
        _bolt(d, ex, np.random.randint(0, 64), 64, 32, k + int(now * 20), 7)


def _corrupt(d, v, now):
    img = frame(d)
    if img is None:
        return
    np.random.seed(int(now * 30) % 99991)
    a = _arr(img)
    amp = int((1.0 - v) * 34)
    for b in range(0, 64, 8):                                  # loss of sync -> horizontal tearing
        if amp > 0:
            a[b:b + 8] = np.roll(a[b:b + 8], np.random.randint(-amp, amp + 1), axis=1)
    a ^= (np.random.random((64, 128)) < _ber(v))               # bit errors
    a &= (np.random.random((64, 128)) < max(0.04, v))          # brightness browns out
    _blit(img, a)


def _draw_short(d, s, now):
    v = _v_discharge(s["pt"])
    stutter = 0.55 + 0.45 * (1 if math.sin(s["pt"] * 22) > -0.3 else 0)   # the rail stutters (failed recoveries)
    _corrupt(d, v * stutter, now)


def _text(d, msg, font, y):
    d.text(((128 - d.textlength(msg, font=font)) / 2, y), msg, font=font, fill=1)


def _draw_dead(d, s):
    d.rectangle([0, 0, 127, 63], fill=0)
    if s["pt"] < 0.4:                                          # the panel's last charge bleeds away
        for _ in range(int((0.4 - s["pt"]) / 0.4 * 120)):
            _put(d, np.random.randint(0, 128), np.random.randint(0, 64), 0.6)
    blink = int(s["pt"] * 1.8) % 2 == 0
    msg = ("POWER LOSS", "SYSTEM FAILURE", "ERR 0x5F")[int(s["pt"] / _T_DEAD * 3) % 3]
    if blink:
        _text(d, msg, _FONT, 20)
    fl = int(s["pt"] * 10) % 128                               # a dead-flat diagnostic line with a stray blip
    for x in range(0, 128, 4):
        _put(d, x, 44, 0.5)
    _put(d, fl, 44 - (4 if fl % 40 < 4 else 0), 0.9)


def _draw_wakefail(d, s, now):
    """A failed wake: the raster claws partway up, then tears itself apart in a glitch and collapses
    back to dark -- Pip tried to boot and couldn't, so it falls back to the error screen."""
    p = s["pt"] / _T_WAKEFAIL
    np.random.seed(int(now * 30) % 99991)
    d.rectangle([0, 0, 127, 63], fill=0)
    sweep = int(min(1.0, p / 0.55) * 64)                       # the scanline rises, trying to lock...
    for x in range(0, 128, 2):
        _put(d, x, sweep, 0.9)
    for yy in range(0, sweep, 3):
        for x in range(0, 128, 4):
            _put(d, x, yy, 0.4)
    _text(d, "BOOT", _FONT_S, 2)
    if p > 0.55:                                               # ...then it glitches out and dies back to dark
        _corrupt(d, 1.0 - (p - 0.55) / 0.45, now)


def _draw_reboot(d, s, now):
    v = _v_recharge(s["pt"])
    img = frame(d)
    np.random.seed(int(now * 30) % 99991)
    if v < 0.30:                                               # backlight flicker, nothing locked yet
        d.rectangle([0, 0, 127, 63], fill=0)
        if np.random.random() < v / 0.30:
            for _ in range(40):
                _put(d, np.random.randint(0, 128), np.random.randint(0, 64), 0.5)
    elif v < _V_ON:                                            # raster: a scanline sweeps the screen up
        d.rectangle([0, 0, 127, 63], fill=0)
        sweep = int((v - 0.30) / (_V_ON - 0.30) * 64)
        for x in range(0, 128, 2):
            d.point((x, sweep), fill=1)
        for yy in range(sweep, 64, 3):
            for x in range(0, 128, 4):
                _put(d, x, yy, 0.4)
        _text(d, "BOOT", _FONT_S, 2)
    elif v < 0.82:                                             # POST: progress bar fills + eyes wipe back in
        prog = (v - _V_ON) / (0.82 - _V_ON)
        if img is not None:
            a = _arr(img) & (_COLS[None, :] < prog * 150)      # reveal the eyes column by column
            a ^= (np.random.random((64, 128)) < 0.05)
            _blit(img, a)
        d.rectangle([14, 58, 114, 61], outline=1)
        d.rectangle([15, 59, 15 + int(prog * 98), 60], fill=1)
        _text(d, "BOOTING", _FONT_S, 1)
    else:                                                      # alive: the last glitch settles out
        _corrupt(d, 1.0 - (1.0 - v) * 0.6, now)


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    _step(now)                                                 # NB: don't clear -- the worn eyes are the live display
    s = _S
    {"calm": lambda: _draw_calm(d, s), "wave": lambda: _draw_wave(d, s, now),
     "surge": lambda: _draw_surge(d, s, now), "short": lambda: _draw_short(d, s, now),
     "dead": lambda: _draw_dead(d, s), "wakefail": lambda: _draw_wakefail(d, s, now),
     "reboot": lambda: _draw_reboot(d, s, now),
     }.get(s["phase"], lambda: None)()                         # 'done' -> draw nothing, _expired clears it


def _expired(now, start):
    return _S.get("phase") == "done"                           # one full run then back to the normal face


VIBE = Vibe("solarflare", mood="scared", overlay=_overlay, expired=_expired, still=True)


# --------------------------------------- real-flare trigger (yesterday's storms, replayed today)
# We can't read the live X-ray feed in real time, so we replay one UTC day behind: ONE request for
# NOAA's flare-event list, keep yesterday's M+ peaks in memory as a time-of-day schedule, and fire
# each at the same wall-clock time today. NOAA's xray-flares feed is the authoritative, no-key list
# of discrete flares (begin/max/end + class); we key off max_time and the M-or-X class letter.
_FLARES = "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json"
_CLASSES = ("M", "X")    # what counts as a real solar storm (C and below are everyday, ignored)
_TICK = 30.0             # s between schedule checks -- local only; the network fetch is once per day
_RETRY = 600.0           # s before retrying the daily fetch if NOAA was unreachable


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "esplink-buddy (github.com/HamzaYslmn/esplink-mcp-robot)"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def _sod(dt):
    return dt.hour * 3600 + dt.minute * 60 + dt.second        # second-of-day, for time-of-day matching


def _parse_flares(rows, day):
    """M+ flares whose peak fell on `day` (UTC) -> sorted [(second-of-day, 'M1.2'), ...]."""
    out = []
    for f in rows:
        peak, cls = f.get("max_time"), (f.get("max_class") or "?")[0]
        if cls not in _CLASSES or not peak:
            continue
        t = datetime.datetime.fromisoformat(peak.replace("Z", "+00:00"))
        if t.date() == day:
            out.append((_sod(t), f["max_class"]))
    return sorted(out)


def _yesterday_flares():
    """One request -> yesterday's (UTC) M+ flare schedule held in memory."""
    yest = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).date()
    return _parse_flares(_get(_FLARES), yest)


def watch(trigger):
    """Replay yesterday's space weather in real time today. On open (and once each UTC day after)
    fetch yesterday's M+ flares into a time-of-day schedule, then fire trigger() as today's clock
    reaches each peak time -- ONE network request per 24h, the loop only ticks the cached schedule.
    Slots already past at boot are marked done (no morning burst when you start in the evening).
    Daemon thread, offline-safe. Robot wires trigger -> the solarflare face."""
    def loop():
        day, schedule, fired = None, [], set()
        while True:
            now = datetime.datetime.now(datetime.timezone.utc)
            if now.date() != day:                              # new UTC day / first open -> the one fetch
                try:
                    schedule = _yesterday_flares()
                except Exception:
                    time.sleep(_RETRY)                         # NOAA down -> back off, keep yesterday's schedule
                    continue
                day = now.date()
                fired = {i for i, (t, _c) in enumerate(schedule) if t <= _sod(now)}   # don't replay past slots
            sod = _sod(now)
            for i, (t, _cls) in enumerate(schedule):
                if i not in fired and sod >= t:                # today reached this flare's peak time
                    fired.add(i)
                    trigger()
            time.sleep(_TICK)
    threading.Thread(target=loop, name="solar-watch", daemon=True).start()


def _selfcheck():
    dis = [_v_discharge(t) for t in np.linspace(0, 3.5, 80)]
    assert all(b <= a + 1e-12 for a, b in zip(dis, dis[1:])), "discharge not monotonic"
    assert dis[0] > 1.0 and dis[-1] < _V_TH, "rail should surge then collapse"
    t_die = _TAU_DIS * math.log(_V_SURGE / _V_TH)
    assert abs(_v_discharge(t_die) - _V_TH) < 1e-9, "discharge crossing wrong"
    assert t_die > 2.0, f"short phase too brief ({t_die:.1f}s) -- want a long staged failure"
    chg = [_v_recharge(t) for t in np.linspace(0, _T_REBOOT, 80)]
    assert all(b >= a - 1e-12 for a, b in zip(chg, chg[1:])) and chg[-1] > 0.9, "recharge should climb high"
    assert _ber(0.5) > _ber(0.9) >= 0.0, "BER should grow as V drops"
    xs = [_front_x(t) for t in (0.0, 0.5, 1.0)]
    assert abs((xs[1] - xs[0]) - (xs[2] - xs[1])) < 1e-9, "front speed not constant"

    _S.update(fluid=None, carry=0.0)                           # wave plasma is a real advected/diffused flow, not a wire
    for i in range(40):
        _S["dt"] = 1 / 30.0
        F = _advance_fluid(_S, i / 30.0)
    filled = F > 0.05
    assert filled.mean() > 0.15, f"plasma too thin -- not gooey ({filled.mean():.2f} filled)"
    assert ((F > 0.1) & (F < 0.9)).mean() > 0.1, "no soft gradient -- gooey plasma needs blurred edges, not on/off"
    cols = int(filled.any(0).sum())
    assert 25 < cols < 110, f"front did not advance as a wall ({cols} cols lit)"

    # the dice mechanic: a fresh ~_P_REBOOT roll per 5s window (deterministic per window)
    hits = sum(rand(s0 * 3.1 + k * 7.31) < _P_REBOOT for s0 in range(200) for k in range(1, 11))
    assert 0.34 < hits / 2000 < 0.46, f"reboot odds off target: {hits / 2000:.2f}"

    # the real-flare trigger: yesterday's M+ peaks -> a time-of-day schedule, replayed today
    yest = datetime.date(2026, 6, 18)
    rows = [{"max_time": "2026-06-18T14:03:00Z", "max_class": "X2.0"},   # yesterday X -> in
            {"max_time": "2026-06-18T09:47:00Z", "max_class": "M1.2"},   # yesterday M -> in (earlier)
            {"max_time": "2026-06-18T02:00:00Z", "max_class": "B5.5"},   # yesterday but only B -> out
            {"max_time": "2026-06-17T23:00:00Z", "max_class": "M9.9"},   # wrong day -> out
            {"max_time": "2026-06-19T01:00:00Z", "max_class": "X1.0"},   # today, not yet -> out
            {"max_time": None, "max_class": "M3"}]                       # no peak time -> out
    sched = _parse_flares(rows, yest)
    assert [c for _, c in sched] == ["M1.2", "X2.0"], f"bad schedule: {sched}"   # only yesterday's M+, by time
    assert sched[0][0] == 9 * 3600 + 47 * 60 and sched[1][0] == 14 * 3600 + 3 * 60, sched
    booted = {i for i, (t, _c) in enumerate(sched) if t <= 10 * 3600}            # start 10:00 -> 09:47 missed
    assert booted == {0}, booted
    due = [i for i, (t, _c) in enumerate(sched) if i not in booted and 15 * 3600 >= t]   # by 15:00 the X fires
    assert due == [1], due

    # a failed boot attempt: wake -> glitch -> back to the error screen (it retries until a roll wakes it)
    seed = next(s for s in range(200) if rand(s + 7.31) >= _P_REBOOT)   # a first attempt that fails
    _S.update(on=True, last=float(seed), phase="dead", pt=0.0, dead_t0=float(seed), attempt=0, dt=1 / 30.0)
    saw = set()
    for i in range(1, int((_T_ROLL + _T_WAKEFAIL + 1.0) * 30)):
        _step(seed + i / 30.0)
        saw.add(_S["phase"])
    assert "wakefail" in saw, f"a failed attempt must glitch-out: {saw}"
    assert _S["phase"] == "dead", f"a failed boot must fall back to the error: {_S['phase']}"

    # plays through once, then self-ends -- no auto-loop back to calm
    _S.update(on=False, last=None)
    order, dur, t = [], {}, 0.0
    while _S.get("phase") != "done" and t < 120.0:
        _step(t)
        if not order or order[-1] != _S["phase"]:
            order.append(_S["phase"])
        dur[_S["phase"]] = dur.get(_S["phase"], 0) + 1
        t += 1 / 30.0
    assert order[:5] == ["calm", "wave", "surge", "short", "dead"], f"bad start: {order}"
    assert order[-2:] == ["reboot", "done"], f"bad end: {order}"
    assert all(p in ("dead", "wakefail") for p in order[5:-2]), f"only error/retry before boot: {order}"
    assert order.count("calm") == 1 and _expired(0.0, 0.0), "must play once then self-end"
    secs = {k: v / 30 for k, v in dur.items()}
    assert secs["dead"] >= _T_ROLL - 0.1, f"dead ended before its first attempt: {secs['dead']:.1f}s"
    print(f"solarflare ok: RC discharge die@{t_die:.1f}s, recharge->{chg[-1]:.2f}; gooey wave; "
          f"error->attempt->glitch loop (5s/{_P_REBOOT:.0%} wake) -> plays once -> done")


def _show_schedule():
    """Live: print the real dates and the M+ flares we'd replay today (what watch() loads on open)."""
    today = datetime.datetime.now(datetime.timezone.utc).date()
    yest = today - datetime.timedelta(days=1)
    print(f"today {today} UTC -- replaying solar flares from {yest}:")
    try:
        rows = _get(_FLARES)
    except Exception as e:
        print(f"  NOAA unreachable ({e}); watch() would retry")
        return
    sched = _parse_flares(rows, yest)
    if not sched:
        print("  no M+ flares yesterday (quiet Sun) -- nothing to replay")
    for sod, cls in sched:
        print(f"  {sod // 3600:02d}:{sod % 3600 // 60:02d}:{sod % 60:02d} UTC  class {cls}  -> fires at this time today")
    print(f"  (feed holds {len(rows)} flares; most recent:)")
    for f in [r for r in rows if r.get("max_time")][-5:]:
        print(f"    {f['max_time']}  class {f.get('max_class', '?')}")


if __name__ == "__main__":
    _selfcheck()
    _show_schedule()
