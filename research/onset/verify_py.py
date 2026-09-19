#!/usr/bin/env python3
"""Independent pure-Python re-implementation of CONVENTIONS.md Langton's Ant.
Cross-checks the C simulator's turn string and trajectory for the first M steps.
Usage: python3 verify_py.py OUTDIR [M]
"""
import sys
out = sys.argv[1]
M = int(sys.argv[2]) if len(sys.argv) > 2 else 15000

DX = [0, 1, 0, -1]; DY = [1, 0, -1, 0]   # N E S W
grid = {}
x = y = 0; d = 0
turns = []; traj = [(0, 0, 0)]
for k in range(1, M + 1):
    c = grid.get((x, y), 0)
    if c == 0:
        d = (d + 1) % 4; turns.append('R')
    else:
        d = (d + 3) % 4; turns.append('L')
    grid[(x, y)] = c ^ 1
    x += DX[d]; y += DY[d]
    traj.append((x, y, d))

ct = open(f"{out}/turns.txt").read().strip()[:M]
assert ct == ''.join(turns), "turn string mismatch"
with open(f"{out}/traj.txt") as f:
    for k in range(M + 1):
        cx, cy, cd = map(int, f.readline().split())
        assert (cx, cy, cd) == traj[k], f"traj mismatch at step {k}"
# independent onset computation on the python turn string (within M)
t = ['?'] + turns
s = 0
for k in range(M - 104, 0, -1):
    if t[k] != t[k + 104]:
        s = k; break
print(f"python cross-check OK for {M} steps; onset within {M} steps = {s}; black cells after {M} steps = {sum(grid.values())}")
