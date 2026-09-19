#!/usr/bin/env python3
"""naive.py -- independent, deliberately simple Langton's-ant simulation used to
sanity-check exhaust.c.  Follows research/CONVENTIONS.md literally:
ant at (0,0) facing North=(0,+1); white -> right turn (N->E), black -> left;
flip; move.  Stores the FULL turn sequence and computes the onset step by the
definition  s = max{k : t[k] != t[k+104]}  over the simulated prefix, then
checks the certification (20 periods + escape by 20 cells) directly.

Usage: python3 naive.py [N] [x,y ...]   (initial black cells as x,y pairs)
"""
import sys

PERIOD = 104

def simulate(black, N):
    grid = set(black)              # set of black cells
    x, y, d = 0, 0, 0              # d: 0=N,1=E,2=S,3=W
    DX = [0, 1, 0, -1]; DY = [1, 0, -1, 0]
    turns = [None]                 # 1-indexed: turns[k] for step k
    pos = [(0, 0)]                 # pos[k] = position after k steps
    modified_at = {}               # cell -> first step it was modified (0 for initial)
    for c in black: modified_at[c] = 0
    for n in range(1, N + 1):
        if (x, y) in grid:
            d = (d - 1) % 4; turns.append('L'); grid.remove((x, y))
        else:
            d = (d + 1) % 4; turns.append('R'); grid.add((x, y))
        modified_at.setdefault((x, y), n)
        x += DX[d]; y += DY[d]
        pos.append((x, y))
    return turns, pos, modified_at

def onset(turns):
    N = len(turns) - 1
    s = 0
    for k in range(1, N - PERIOD + 1):
        if turns[k] != turns[k + PERIOD]: s = k
    return s

def certify(turns, pos, modified_at, s):
    N = len(turns) - 1
    periods_verified = (N - PERIOD - s) // PERIOD
    cells = [c for c, st in modified_at.items() if st <= s] + [(0, 0)]
    bx0 = min(c[0] for c in cells); bx1 = max(c[0] for c in cells)
    by0 = min(c[1] for c in cells); by1 = max(c[1] for c in cells)
    # direction of travel from the last period, escape checked at final position
    dx = pos[N][0] - pos[N - PERIOD][0]; dy = pos[N][1] - pos[N - PERIOD][1]
    x, y = pos[N]
    okx = (x >= bx1 + 20) if dx > 0 else (x <= bx0 - 20)
    oky = (y >= by1 + 20) if dy > 0 else (y <= by0 - 20)
    # earliest step at which certification (both conditions) holds
    cert_step = None
    for n in range(s + PERIOD + 20 * PERIOD, N + 1):
        px, py = pos[n]
        ddx = px - pos[n - PERIOD][0]; ddy = py - pos[n - PERIOD][1]
        if ddx == 0 or ddy == 0: continue
        ox = (px >= bx1 + 20) if ddx > 0 else (px <= bx0 - 20)
        oy = (py >= by1 + 20) if ddy > 0 else (py <= by0 - 20)
        if ox and oy: cert_step = n; break
    # per-period footprint (spatial extent of the ant's positions within one period)
    xs = [pos[n][0] for n in range(N - PERIOD, N + 1)]; ys = [pos[n][1] for n in range(N - PERIOD, N + 1)]
    return dict(periods_verified=periods_verified, bbox=[bx0, by0, bx1, by1], disp=[dx, dy],
                direction=("+x" if dx > 0 else "-x") + "," + ("+y" if dy > 0 else "-y"),
                escaped_at_N=bool(okx and oky and dx != 0 and dy != 0), cert_step=cert_step,
                period_footprint=[max(xs) - min(xs), max(ys) - min(ys)], final_pos=list(pos[N]))

if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    black = [tuple(int(v) for v in a.split(',')) for a in sys.argv[2:]]
    turns, pos, mod = simulate(black, N)
    s = onset(turns)
    c = certify(turns, pos, mod, s)
    print("N=%d black=%s" % (N, black))
    print("onset_step s=%d" % s)
    print("first 12 turns:", "".join(turns[1:13]))
    for kk, v in c.items(): print("%s=%s" % (kk, v))
