#!/usr/bin/env python3
"""Independent Langton's-ant simulator written from research/CONVENTIONS.md for
the review of research/exhaustive/.  NOT derived from exhaust.c or naive.py.

Conventions: ant at (0,0) facing N=(0,+1). Headings 0=N,1=E,2=S,3=W; right
turn = +1 (clockwise N->E), left turn = -1.  Step: read cell, white->right,
black->left, flip, move.  t[k]=1 if step k turned right.
Onset s = max{k>=1 : t[k] != t[k+104]} (0 if none).
Certification at the first n >= s + 104 + 20*104 such that the displacement
over the last 104 steps is nonzero in both coordinates and the ant is >= 20
cells beyond the bounding box (initial black cells, origin, cells modified in
steps 1..s) in both coordinates in the direction of travel.
Extra diagnostics: heading periodicity at certification, per-period footprint,
and the true maximum |coordinate| over the whole trajectory.
"""
P = 104
DXY = ((0, 1), (1, 0), (0, -1), (-1, 0))

def simulate(black, N):
    grid = {c: 1 for c in black}
    first_mod = {c: 0 for c in black}
    x = y = 0; d = 0
    turns = [None]; pos = [(0, 0)]; head = [0]
    maxabs = 0
    for n in range(1, N + 1):
        c = grid.get((x, y), 0)
        if c == 0:
            d = (d + 1) % 4; turns.append(1)
        else:
            d = (d - 1) % 4; turns.append(0)
        grid[(x, y)] = 1 - c
        if (x, y) not in first_mod: first_mod[(x, y)] = n
        x += DXY[d][0]; y += DXY[d][1]
        pos.append((x, y)); head.append(d)
        if abs(x) > maxabs: maxabs = abs(x)
        if abs(y) > maxabs: maxabs = abs(y)
    return turns, pos, head, first_mod, maxabs

def onset(turns):
    N = len(turns) - 1
    s = 0
    for k in range(1, N - P + 1):
        if turns[k] != turns[k + P]: s = k
    return s

def analyse(black, N):
    turns, pos, head, first_mod, maxabs = simulate(black, N)
    s = onset(turns)
    cells = [c for c, m in first_mod.items() if m <= s] + [(0, 0)]
    bx0 = min(c[0] for c in cells); bx1 = max(c[0] for c in cells)
    by0 = min(c[1] for c in cells); by1 = max(c[1] for c in cells)
    cert = None; disp = None
    for n in range(s + P + 20 * P, N + 1):
        dx = pos[n][0] - pos[n - P][0]; dy = pos[n][1] - pos[n - P][1]
        if dx == 0 or dy == 0: continue
        px, py = pos[n]
        okx = px >= bx1 + 20 if dx > 0 else px <= bx0 - 20
        oky = py >= by1 + 20 if dy > 0 else py <= by0 - 20
        if okx and oky:
            cert = n; disp = (dx, dy); break
    out = dict(s=s, cert=cert, bbox=(bx0, by0, bx1, by1), maxabs_traj=maxabs)
    if cert is not None:
        dx, dy = disp
        out.update(disp=disp, dir=("+x" if dx > 0 else "-x") + "," + ("+y" if dy > 0 else "-y"),
                   final=pos[cert], heading_periodic=(head[cert] == head[cert - P]),
                   footprint=(max(p[0] for p in pos[cert - P:cert + 1]) - min(p[0] for p in pos[cert - P:cert + 1]),
                              max(p[1] for p in pos[cert - P:cert + 1]) - min(p[1] for p in pos[cert - P:cert + 1])),
                   maxabs_upto_cert=max(max(abs(p[0]), abs(p[1])) for p in pos[:cert + 1]))
    return out

def cells_of(k, cfg):
    m = -(k // 2)
    return [(m + i % k, m + i // k) for i in range(k * k) if (cfg >> i) & 1]

if __name__ == "__main__":
    import sys
    N = int(sys.argv[1]); black = [tuple(int(v) for v in a.split(',')) for a in sys.argv[2:]]
    print(analyse(black, N))
