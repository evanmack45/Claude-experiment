#!/usr/bin/env python3
"""Reconcile the literature's "9977" with CONVENTIONS.md.

Simulates Langton's ant exactly as in research/CONVENTIONS.md (empty grid, ant at
(0,0) facing North, white -> turn right, black -> turn left, flip, move) and
compares the colour read at each step with OEIS A261990 (b-file
data/b261990.txt, downloaded 2026-09-19 from https://oeis.org/A261990/b261990.txt).

Prints, and writes to ../results/literature.json (key "oeis_reconciliation"):
  * number of mismatches between our colour sequence and the b-file,
  * the OEIS index n0 from which b(n) == b(n+104) holds for the rest of the b-file,
  * the corresponding CONVENTIONS onset step s (steps completed before the
    104-periodic regime), and the 1-based number of the first periodic step.

Run:  python3 check_oeis.py
"""
import json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BFILE = os.path.join(HERE, "data", "b261990.txt")
if not os.path.exists(BFILE):
    urllib.request.urlretrieve("https://oeis.org/A261990/b261990.txt", BFILE)

b = {}
for line in open(BFILE):
    p = line.split()
    if len(p) == 2 and not p[0].startswith("#"):
        b[int(p[0])] = int(p[1])
nmin, nmax = min(b), max(b)
N = nmax + 1  # number of steps to simulate

grid = {}
x = y = 0
d = 0  # 0=N,1=E,2=S,3=W ; right turn = +1 (clockwise), left turn = -1
dx = [0, 1, 0, -1]
dy = [1, 0, -1, 0]
colors, turns = [], []
for k in range(1, N + 1):          # step k reads the cell under the ant
    c = grid.get((x, y), 0)
    colors.append(c)
    if c == 0:
        d = (d + 1) % 4; turns.append("R")
    else:
        d = (d - 1) % 4; turns.append("L")
    grid[(x, y)] = 1 - c
    x += dx[d]; y += dy[d]

# OEIS offset is 0: b(n) is compared with the colour read at step n+1.
mism_off0 = [n for n in range(nmin, nmax + 1) if b[n] != colors[n]]
mism_off1 = [n for n in range(max(nmin, 1), nmax + 1) if b[n] != colors[n - 1]]

def periodic_from(seq, P=104):
    """smallest i such that seq[j] == seq[j+P] for all j >= i with j+P < len(seq)"""
    L = len(seq)
    for j in range(L - P - 1, -1, -1):
        if seq[j] != seq[j + P]:
            return j + 1
    return 0

bseq = [b[n] for n in range(nmin, nmax + 1)]
n0_oeis = nmin + periodic_from(bseq)
i0_ours = periodic_from(colors)          # 0-based index into colors == step i0+1
s_conventions = i0_ours                   # steps completed before periodic regime
first_periodic_step = i0_ours + 1

out = {
    "bfile": "data/b261990.txt (OEIS A261990, offset %d, n=%d..%d)" % (nmin, nmin, nmax),
    "steps_simulated": N,
    "mismatches_b(n)_vs_colour_read_at_step_n_plus_1": len(mism_off0),
    "mismatches_b(n)_vs_colour_read_at_step_n": len(mism_off1),
    "oeis_index_from_which_b_is_104_periodic": n0_oeis,
    "conventions_onset_step_s": s_conventions,
    "first_periodic_step_1_based": first_periodic_step,
    "turn_at_step_s_and_s_plus_104": [turns[s_conventions - 1], turns[s_conventions - 1 + 104]],
    "turn_at_step_s_plus_1_and_s_plus_105": [turns[s_conventions], turns[s_conventions + 104]],
    "interpretation": ("OEIS A261990 has offset 0, so b(n) is the colour read at step n+1 in CONVENTIONS "
                       "numbering. The OEIS comment 'begins repeating at the 9977th step' means b(n)==b(n+104) "
                       "for n>=9977, i.e. the turn sequence is periodic from step 9978 onward, i.e. onset step "
                       "s=9977 in CONVENTIONS.md (9977 steps completed before the periodic regime)."),
}
print(json.dumps(out, indent=1))
sys.exit(0 if (len(mism_off0) == 0 and s_conventions == 9977) else 1)
