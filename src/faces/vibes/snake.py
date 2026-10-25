"""Snake -- Pip plays itself a *guaranteed* perfect game. A precomputed Hamiltonian cycle visits
every cell once and loops, so just following it can never crash and always fills the board to 100%.
On top of that the head takes safe shortcuts while the board is less than half full -- it hops to an
adjacent cell that jumps forward toward the food without overtaking its own tail -- so it beelines
for the apple instead of plodding the whole loop. Past the halfway mark shortcuts switch off and the
pure cycle takes over, which is what makes the win a certainty (A* alone never finishes -- it boxes
itself in around 75% and survives forever without completing).

Dirt cheap: one cycle is precomputed at import; each step is a dict lookup plus at most four neighbour
checks -- no A*, no flood fill, no per-frame allocation beyond the snake list. Stateful: advances by
real elapsed time, rebuilds on (re)start, restarts when the board is full."""
from ..primitives import rand
from ..spec import Vibe

CELL = 5                                  # px per grid cell
COLS, ROWS = 24, 12                       # ROWS must stay even so the cycle closes (120x60 area)
OX, OY = 4, 2                             # board offset -> centred on the 128x64 panel
TICK = 0.05                               # seconds per snake step

# -- Hamiltonian cycle: serpentine over columns 1..COLS-1, then a return spine up column 0 --
_ORDER = []
for _row in range(ROWS):
    _xs = range(1, COLS) if _row % 2 == 0 else range(COLS - 1, 0, -1)
    _ORDER += [(x, _row) for x in _xs]
_ORDER += [(0, _row) for _row in range(ROWS - 1, -1, -1)]   # ROWS even -> serpentine ends at (1,ROWS-1)
N = len(_ORDER)                                              # == COLS * ROWS
CYC = {c: i for i, c in enumerate(_ORDER)}                   # cell -> position in the cycle


def _neighbors(c):
    x, y = c
    if x + 1 < COLS: yield (x + 1, y)
    if x - 1 >= 0:   yield (x - 1, y)
    if y + 1 < ROWS: yield (x, y + 1)
    if y - 1 >= 0:   yield (x, y - 1)


def _next(snake, food):
    """The next head cell: a safe shortcut toward the food if the board's roomy, else the cycle step.
    No occupancy lookup needed -- a cell whose forward cycle-gap is in (0, d_tail) is provably free,
    so the index test alone picks only empty cells (verified over millions of ticks)."""
    head = snake[0]
    h = CYC[head]
    d_tail = (CYC[snake[-1]] - h) % N                       # forward gap head->tail along the cycle
    d_food = (CYC[food] - h) % N
    if N - len(snake) > N // 2:                             # shortcuts only while < half full (anti-trap)
        best, best_d = None, 0
        for n in _neighbors(head):
            d = (CYC[n] - h) % N
            if 0 < d < d_tail and d <= d_food and d > best_d:   # ahead, before the tail, not past the food
                best, best_d = n, d
        if best is not None:
            return best
    return _ORDER[(h + 1) % N]                              # strict cycle step -- always safe, guarantees the win


def _spawn_food(snake, salt):
    free = [c for c in _ORDER if c not in snake]
    return free[int(rand(len(snake), salt) * len(free))] if free else None


def _new_game():
    snake = [_ORDER[2], _ORDER[1], _ORDER[0]]              # head first, laid along the cycle -> valid start
    return {"snake": snake, "food": _spawn_food(set(snake), 0), "acc": 0.0, "last": None, "score": 0}


_S = _new_game()                                           # live game; module-level (one engine)


def _step(g):
    snake = g["snake"]
    move = _next(snake, g["food"])
    snake.insert(0, move)
    if move == g["food"]:                                  # eat: grow (no tail pop)
        g["score"] += 1
        if len(snake) >= N:                               # board full -> 100%, restart
            g.update(_new_game())
            return
        g["food"] = _spawn_food(set(snake), g["score"])
    else:
        snake.pop()                                       # tail follows


def _overlay(d, W, H, now, ox=0.0, oy=0.0):
    g = _S
    if g["last"] is None or now < g["last"] or now - g["last"] > 1.0:
        g.update(_new_game())                             # first frame / restart / long stall -> fresh game
    g["acc"] += now - g["last"] if g["last"] is not None else 0.0
    g["last"] = now
    while g["acc"] >= TICK:                               # fixed-step, frame-rate independent
        g["acc"] -= TICK
        _step(g)

    d.rectangle([0, 0, W - 1, H - 1], fill=0)             # the game owns the whole face

    fx, fy = g["food"]                                    # blinking apple -> tells food from body
    if int(now * 3) % 2:
        px, py = OX + fx * CELL, OY + fy * CELL
        d.rectangle([px, py, px + CELL - 2, py + CELL - 2], fill=1)

    for i, (cx, cy) in enumerate(g["snake"]):
        px, py = OX + cx * CELL, OY + cy * CELL
        s = CELL - 1 if i else CELL                       # head is a full solid block, body leaves a 1px gap
        d.rectangle([px, py, px + s - 1, py + s - 1], fill=1)


VIBE = Vibe("snake", mood="focused", overlay=_overlay, still=True)


if __name__ == "__main__":                               # self-check: valid cycle + EVERY game fills to 100%
    assert N == COLS * ROWS and len(CYC) == N, "cycle must visit every cell once"
    for i in range(N):
        a, b = _ORDER[i], _ORDER[(i + 1) % N]
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1, f"cycle step {a}->{b} not adjacent"
    games = ticks = 0
    g = _new_game()
    for _ in range(2_000_000):
        ticks += 1
        pre = len(g["snake"])
        _step(g)
        assert len(set(g["snake"])) == len(g["snake"]), "snake collided -- 100% guarantee broken"
        if pre >= N - 1 and len(g["snake"]) <= 3:        # just won and reset
            games += 1
    print(f"ok: {games} games all reached 100% ({N} cells), no collisions, {ticks/max(games,1):.0f} ticks/game")
