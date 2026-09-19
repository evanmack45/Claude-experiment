#!/usr/bin/env python3
"""Independent re-derivation of claim C3 (verifier's own code, written from CONVENTIONS.md).

Simulates Langton's ant: origin, facing North=(0,+1); N->E->S->W clockwise = right turn;
white(0) -> turn right, black(1) -> turn left; flip; move. t[k] = 'R'/'L' at step k (1-based).
Onset s = smallest s>=0 with t[k]==t[k+104] for all k>=s+1 within the simulated horizon.
Also compares the colour read at each step with OEIS A261990 b-file at both index offsets.
Usage: python3 ant_oeis_check.py [bfile] [nsteps]
"""
import sys, os
bfile = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "b261990_verifier.txt")
NSTEPS = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
P = 104

DX = {'N': 0, 'E': 1, 'S': 0, 'W': -1}
DY = {'N': 1, 'E': 0, 'S': -1, 'W': 0}
RIGHT = {'N': 'E', 'E': 'S', 'S': 'W', 'W': 'N'}
LEFT = {v: k for k, v in RIGHT.items()}

black = set()
x, y, h = 0, 0, 'N'
turns = []   # turns[k-1] = turn at step k
colour = []  # colour[k-1] = colour read at step k
pos = [(0, 0)]
for k in range(1, NSTEPS + 1):
    c = 1 if (x, y) in black else 0
    colour.append(c)
    if c == 0:
        h = RIGHT[h]; turns.append('R'); black.add((x, y))
    else:
        h = LEFT[h]; turns.append('L'); black.discard((x, y))
    x += DX[h]; y += DY[h]
    pos.append((x, y))

# onset: smallest s such that turns[k-1]==turns[k-1+P] for all k>=s+1 with k+P<=NSTEPS
last_bad = 0  # largest k with t[k]!=t[k+P]
for k in range(1, NSTEPS - P + 1):
    if turns[k - 1] != turns[k - 1 + P]:
        last_bad = k
s = last_bad  # periodic from step last_bad+1 onward
print("steps simulated:", NSTEPS)
print("onset s =", s, "(first periodic step =", s + 1, ")")
print("t[s], t[s+104] =", turns[s - 1], turns[s - 1 + P], "; t[s+1], t[s+105] =", turns[s], turns[s + P])
# displacement per period after onset
p0 = pos[s]; p1 = pos[s + P]; p2 = pos[s + 2 * P]
print("position after s steps:", p0, "after s+104:", p1, "after s+208:", p2, "drift/period:", (p1[0] - p0[0], p1[1] - p0[1]))
print("periods verified within horizon:", (NSTEPS - s) // P)
# bounding box of cells modified before step s+1 (i.e., cells visited at steps 1..s)
vis = pos[:s]
bb = (min(a for a, b in vis), max(a for a, b in vis), min(b for a, b in vis), max(b for a, b in vis))
print("bbox of cells modified in steps 1..s (xmin,xmax,ymin,ymax):", bb, "ant pos at end:", pos[-1])

# OEIS comparison
if os.path.exists(bfile):
    b = {}
    for line in open(bfile):
        p = line.split()
        if len(p) == 2 and p[0].lstrip('-').isdigit():
            b[int(p[0])] = int(p[1])
    nmin, nmax = min(b), max(b)
    print("bfile indices", nmin, "..", nmax, "count", len(b))
    m0 = sum(1 for n in b if n < NSTEPS and b[n] != colour[n])          # b(n) == colour at step n+1
    m1 = sum(1 for n in b if 1 <= n <= NSTEPS and b[n] != colour[n - 1])  # b(n) == colour at step n
    print("mismatches b(n) vs colour read at step n+1:", m0)
    print("mismatches b(n) vs colour read at step n  :", m1)
    # periodicity of b-file itself
    lb = -1
    for n in range(nmin, nmax - P + 1):
        if b[n] != b[n + P]:
            lb = n
    print("b-file: smallest index n0 with b(n)==b(n+104) for all n>=n0:", lb + 1)
    # also check the 'reflected' rule (white->left) gives the same colour sequence
else:
    print("no bfile at", bfile)
