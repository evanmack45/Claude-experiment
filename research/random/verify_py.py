#!/usr/bin/env python3
"""Independent pure-Python cross-check of randexp.c.

Re-implements (1) the splitmix64 sampling scheme, (2) the ant on a dict grid,
(3) the CONVENTIONS onset s = max{k : t[k] != t[k+104]} computed from the full
turn string, (4) the certification step, and compares with the rows randexp.c
wrote for a subset of samples (first 3 samples of every (k,p) cell plus every
sample whose C-reported onset is < 40000 among the first 20 of each cell).
Also asserts the empty grid gives s = 9977.
Prints a summary and exits nonzero on any disagreement.
"""
import csv, sys, os, json
D = os.path.dirname(os.path.abspath(__file__))
M = (1 << 64) - 1
PERIOD, CERT_LEN, MARGIN = 104, 2184, 20

def splitmix_stream(state):
    while True:
        state = (state + 0x9E3779B97F4A7C15) & M
        z = state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M
        yield z ^ (z >> 31)

def gen_config(k, p, seed, idx):
    p1000 = int(round(1000 * p))
    st = (seed * 0x9E3779B97F4A7C15 + idx * 0xBF58476D1CE4E5B9 + k * 0x94D049BB133111EB + p1000 * 0xD6E8FEB86659FD93) & M
    g = splitmix_stream(st)
    xmin = -(k // 2)
    black = set()
    for i in range(k * k):
        r = next(g)
        u = (r >> 11) * (1.0 / 9007199254740992.0)
        if u < p:
            black.add((xmin + i % k, xmin + i // k))
    return black

def simulate(black, nsteps):
    """Return turn string t[1..n] and positions pos[0..n]."""
    grid = dict((c, 1) for c in black)
    DX = [0, 1, 0, -1]; DY = [1, 0, -1, 0]
    x = y = d = 0
    T = []; P = [(0, 0)]
    for _ in range(nsteps):
        c = grid.get((x, y), 0)
        if c == 0: d = (d + 1) & 3; T.append('R')
        else:      d = (d + 3) & 3; T.append('L')
        grid[(x, y)] = c ^ 1
        x += DX[d]; y += DY[d]
        P.append((x, y))
    return ''.join(T), P

def analyze(black, nsteps):
    T, P = simulate(black, nsteps)
    t = lambda k: T[k - 1]
    s = 0
    for k in range(nsteps - PERIOD, 0, -1):
        if t(k) != t(k + PERIOD): s = k; break
    # bbox of origin, initial black cells, cells modified in steps 1..s (positions 0..s-1)
    pts = [(0, 0)] + list(black) + P[:s]
    bx0 = min(q[0] for q in pts); bx1 = max(q[0] for q in pts)
    by0 = min(q[1] for q in pts); by1 = max(q[1] for q in pts)
    cert = None; disp = None
    for n in range(s + CERT_LEN, nsteps + 1):
        dx = P[n][0] - P[n - PERIOD][0]; dy = P[n][1] - P[n - PERIOD][1]
        if dx == 0 or dy == 0: continue
        okx = P[n][0] >= bx1 + MARGIN if dx > 0 else P[n][0] <= bx0 - MARGIN
        oky = P[n][1] >= by1 + MARGIN if dy > 0 else P[n][1] <= by0 - MARGIN
        if okx and oky: cert = n; disp = (dx, dy); break
    dirname = None
    if disp: dirname = ('+x' if disp[0] > 0 else '-x') + ',' + ('+y' if disp[1] > 0 else '-y')
    return s, cert, dirname, (bx0, by0, bx1, by1)

def main():
    s0, c0, d0, _ = analyze(set(), 20000)
    assert (s0, c0, d0) == (9977, 12336, '-x,-y'), (s0, c0, d0)
    print('empty grid: s=9977 cert=12336 dir=-x,-y  OK')
    rows = []
    for f in ('out/procA.csv', 'out/procB.csv'):
        with open(os.path.join(D, f)) as fh:
            for r in csv.reader(fh):
                rows.append(r)
    bycell = {}
    for r in rows:
        bycell.setdefault((int(r[0]), float(r[1])), []).append(r)
    nchecked = 0; nfail = 0
    for cell, rs in sorted(bycell.items()):
        rs = sorted(rs, key=lambda r: int(r[3]))
        chosen = rs[:3] + [r for r in rs[3:20] if int(r[5]) < 40000]
        for r in chosen:
            k, p, seed, idx = int(r[0]), float(r[1]), int(r[2]), int(r[3])
            outcome, s_c, dir_c, steps_c, nblack_c = r[4], int(r[5]), r[6], int(r[7]), int(r[8])
            if outcome != 'certified': continue
            black = gen_config(k, p, seed, idx)
            s, cert, dirname, bbox = analyze(black, steps_c + 300)
            ok = (len(black) == nblack_c and s == s_c and cert == steps_c and dirname == dir_c
                  and bbox == (int(r[13]), int(r[14]), int(r[15]), int(r[16])))
            nchecked += 1
            if not ok:
                nfail += 1
                print('MISMATCH', cell, idx, 'py:', (len(black), s, cert, dirname, bbox), 'c:', (nblack_c, s_c, steps_c, dir_c, r[13:17]))
    print(f'checked {nchecked} certified samples against pure Python: {nfail} mismatches')
    json.dump({'n_checked': nchecked, 'n_mismatch': nfail, 'empty_grid_s': s0, 'empty_grid_cert_step': c0},
              open(os.path.join(D, 'out', 'verify_py.json'), 'w'), indent=1)
    sys.exit(1 if nfail else 0)

if __name__ == '__main__':
    main()
