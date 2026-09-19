#!/usr/bin/env python3
"""Per-period footprint of the highway (empty grid) as a function of window phase,
plus the width of the strip of highway cells perpendicular to the travel direction."""
from literal import sim
P = 104
t, pos = sim([], 20000)
ext = set()
for n in range(15000, 15000 + P):
    xs = [pos[q][0] for q in range(n - P, n + 1)]; ys = [pos[q][1] for q in range(n - P, n + 1)]
    ext.add((max(xs) - min(xs), max(ys) - min(ys)))
print("footprint extents (dx,dy) over all 104 window phases:", sorted(ext))
n = 20000
xs = [pos[q][0] for q in range(n - P, n + 1)]; ys = [pos[q][1] for q in range(n - P, n + 1)]
print("naive.py's phase (window N-104..N, N=20000):", (max(xs) - min(xs), max(ys) - min(ys)))
# all cells visited from step 15000 on: width of the strip perpendicular to (-1,-1) travel = range of (x - y)
cells = set(pos[q] for q in range(15000, 20000))
w = [c[0] - c[1] for c in cells]
print("strip: range of x-y over highway cells =", min(w), max(w), "-> perpendicular width (cells) =", max(w) - min(w) + 1)
