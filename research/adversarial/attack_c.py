#!/usr/bin/env python3
"""Attack C: hand-designed structured initial configurations, simulated with
./antsim batch (cap 50,000,000, grid 8192). Writes out/attack_c.jsonl and
out/attack_c_summary.json.   Usage: python3 attack_c.py"""
import json, subprocess, os, sys
here = os.path.dirname(os.path.abspath(__file__))
def box_lo(n): return -(n // 2)          # CONVENTIONS.md box: -floor(n/2) .. (odd) / -n/2 .. n/2-1 (even)
cfgs = []
def add(name, family, cells): cfgs.append(dict(name=name, family=family, cells=sorted(set(cells))))
for n in range(2, 13):
    lo = box_lo(n); add(f'filled_square_{n}', 'filled_square', [(x, y) for x in range(lo, lo+n) for y in range(lo, lo+n)])
for n in (16, 20, 30, 50):
    lo = box_lo(n); add(f'filled_square_{n}', 'filled_square_large', [(x, y) for x in range(lo, lo+n) for y in range(lo, lo+n)])
for n in range(3, 13):
    lo = box_lo(n); add(f'hollow_square_{n}', 'hollow_square', [(x, y) for x in range(lo, lo+n) for y in range(lo, lo+n) if x in (lo, lo+n-1) or y in (lo, lo+n-1)])
for n in (20, 30):
    lo = box_lo(n); add(f'hollow_square_{n}', 'hollow_square', [(x, y) for x in range(lo, lo+n) for y in range(lo, lo+n) if x in (lo, lo+n-1) or y in (lo, lo+n-1)])
for L in range(2, 31):
    add(f'hline_{L}', 'hline', [(i, 0) for i in range(L)])
    add(f'vline_{L}', 'vline', [(0, i) for i in range(L)])
    add(f'diag_{L}', 'diag', [(i, i) for i in range(L)])
    add(f'antidiag_{L}', 'antidiag', [(i, -i) for i in range(L)])
for L in (5, 11, 21, 31):   # lines centred on the origin
    h = L // 2
    add(f'hline_centred_{L}', 'hline_centred', [(i, 0) for i in range(-h, h+1)])
    add(f'vline_centred_{L}', 'vline_centred', [(0, i) for i in range(-h, h+1)])
    add(f'diag_centred_{L}', 'diag_centred', [(i, i) for i in range(-h, h+1)])
for n in (4, 6, 8, 12, 16):
    lo = box_lo(n)
    for par in (0, 1):
        add(f'checkerboard_{n}_par{par}', 'checkerboard', [(x, y) for x in range(lo, lo+n) for y in range(lo, lo+n) if (x + y) % 2 == par])
for n in (5, 9, 13, 21):
    h = n // 2
    add(f'plus_{n}', 'cross_plus', [(i, 0) for i in range(-h, h+1)] + [(0, i) for i in range(-h, h+1)])
    add(f'xcross_{n}', 'cross_x', [(i, i) for i in range(-h, h+1)] + [(i, -i) for i in range(-h, h+1)])
for dx in (-1, 0, 1):
    for dy in (-1, 0, 1):
        if (dx, dy) != (0, 0): add(f'single_{dx}_{dy}', 'single_neighbour', [(dx, dy)])
add('single_origin', 'single_neighbour', [(0, 0)])
add('ring8', 'ring', [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)])
for n in (3, 5, 7, 11):
    h = n // 2; add(f'diamond_{n}', 'diamond', [(x, y) for x in range(-h, h+1) for y in range(-h, h+1) if abs(x) + abs(y) <= h])
for n in (3, 5, 7):
    h = n // 2; add(f'hollow_diamond_{n}', 'hollow_diamond', [(x, y) for x in range(-h, h+1) for y in range(-h, h+1) if abs(x) + abs(y) == h])
for k in (5, 9, 13):
    add(f'concentric_rings_{k}', 'concentric', [(x, y) for x in range(-(k//2), k//2+1) for y in range(-(k//2), k//2+1) if max(abs(x), abs(y)) % 2 == 0])
for n in (4, 8, 12):
    lo = box_lo(n); add(f'stripes_h_{n}', 'stripes', [(x, y) for x in range(lo, lo+n) for y in range(lo, lo+n) if y % 2 == 0])
    add(f'stripes_v_{n}', 'stripes', [(x, y) for x in range(lo, lo+n) for y in range(lo, lo+n) if x % 2 == 0])
add('best_k5_exhaustive', 'reference', [(0,-2),(2,-2),(-2,-1),(-1,-1),(2,-1),(0,1),(2,1),(-2,2),(0,2),(1,2),(2,2)])
add('best_k4_exhaustive', 'reference', [(-2,-2),(1,-2),(0,-1),(1,-1),(-2,0),(-1,0),(-2,1),(-1,1),(0,1)])
# the empty-grid highway's own pattern as a seed: black cells of the empty grid at step 9977 (pre-onset), computed here
DX = [0, 1, 0, -1]; DY = [1, 0, -1, 0]; black = set(); x = y = d = 0
for k in range(1, 9978):
    if (x, y) in black: d = (d + 3) % 4; black.discard((x, y))
    else: d = (d + 1) % 4; black.add((x, y))
    x += DX[d]; y += DY[d]
add('empty_grid_state_at_onset', 'reference', sorted(black))
add('empty', 'reference', [])

inp = '\n'.join(' '.join(f'{cx},{cy}' for cx, cy in c['cells']) for c in cfgs) + '\n'
proc = subprocess.run([os.path.join(here, 'antsim'), 'batch', '--cap', '50000000', '--grid', '8192'], input=inp, capture_output=True, text=True)
lines = proc.stdout.strip().split('\n'); assert len(lines) == len(cfgs), proc.stderr[:300]
res = []
with open(os.path.join(here, 'out', 'attack_c.jsonl'), 'w') as f:
    for c, ln in zip(cfgs, lines):
        r = json.loads(ln); r.update(name=c['name'], family=c['family'], n_cells=len(c['cells']), cells=c['cells'])
        res.append(r); f.write(json.dumps(r) + '\n')
oc = {}
for r in res: oc[r['outcome']] = oc.get(r['outcome'], 0) + 1
best = max(res, key=lambda r: r['onset_step'])
fam = {}
for r in res: fam.setdefault(r['family'], []).append(r)
summary = dict(n_configs=len(res), outcome_counts=oc, cap_hits=[r['name'] for r in res if r['outcome'] != 'certified'],
               longest=dict(name=best['name'], onset_step=best['onset_step'], direction=best['direction'], cells=best['cells']),
               top10=[dict(name=r['name'], onset_step=r['onset_step'], direction=r['direction']) for r in sorted(res, key=lambda r: -r['onset_step'])[:10]],
               per_family={k: dict(n=len(v), max_onset=max(r['onset_step'] for r in v), max_name=max(v, key=lambda r: r['onset_step'])['name'],
                                   min_onset=min(r['onset_step'] for r in v)) for k, v in fam.items()},
               table=[dict(name=r['name'], n_cells=r['n_cells'], onset_step=r['onset_step'], outcome=r['outcome'], direction=r['direction']) for r in res])
json.dump(summary, open(os.path.join(here, 'out', 'attack_c_summary.json'), 'w'), indent=1)
print(json.dumps({k: v for k, v in summary.items() if k != 'table'}, indent=1))
