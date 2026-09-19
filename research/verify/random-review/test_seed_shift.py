#!/usr/bin/env python3
"""Defect check: randexp.c seeds splitmix64 with state = seed*GAMMA + ..., where GAMMA
is splitmix64's own increment. Hence seed+1 == same stream advanced by ONE output, so
sample idx of seed S+1 is sample idx of seed S with the raster index shifted by one cell
(config'[i] = config[i+1]) plus one fresh cell. This script demonstrates it with
./randexp dump and measures the resulting onset correlation between the main sweep
(seed 20260919) and the extended sweep (seed 20260920) at the same sample_index."""
import subprocess, json, csv, os
import numpy as np
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'random')
def dump(k, p, seed, idx):
    j = json.loads(subprocess.run([R + '/randexp', 'dump', str(k), str(p), str(seed), str(idx)], capture_output=True, text=True, check=True).stdout)
    xmin = -(k // 2)
    return set((x - xmin) + k * (y - xmin) for x, y in j['black_cells'])
ok = True
for (k, p, idx) in [(5, 0.5, 0), (8, 0.1, 7), (64, 0.75, 4491), (32, 0.9, 123)]:
    a = dump(k, p, 20260919, idx); b = dump(k, p, 20260920, idx); c = dump(k, p, 20260921, idx)
    n = k * k
    # b[i] should equal a[i+1] for i in 0..n-2 ; c[i] == a[i+2]
    shift1 = all(((i in b) == ((i + 1) in a)) for i in range(n - 1))
    shift2 = all(((i in c) == ((i + 2) in a)) for i in range(n - 2))
    print(f'k={k} p={p} idx={idx}: seed+1 is raster-shift-by-1 of seed: {shift1}; seed+2 is shift-by-2: {shift2}')
    ok &= shift1 and shift2
# onset correlation main(seed 20260919) vs ext(seed 20260920), same idx, per cell
main = {}
for f in ('procA.csv', 'procB.csv'):
    for r in csv.reader(open(os.path.join(R, 'out', f))):
        main.setdefault((int(r[0]), float(r[1])), {})[int(r[3])] = int(r[5])
print('onset Spearman-ish (Pearson on log) correlation main vs ext at same sample_index, and vs ext idx+1 (control):')
for (k, p) in [(5, 0.5), (16, 0.5), (32, 0.5), (64, 0.5), (64, 0.9)]:
    ext = np.fromfile(os.path.join(R, 'out', 'ext', f'k{k}_p{p}.u32'), dtype=np.uint32).astype(np.int64)
    m = np.array([main[(k, p)][i] for i in range(10000)])
    e = ext[:10000]; e1 = ext[1:10001]
    c_same = np.corrcoef(np.log(m), np.log(e))[0, 1]; c_ctrl = np.corrcoef(np.log(m), np.log(e1))[0, 1]
    ident = int((m == e).sum())
    print(f'  k={k} p={p}: corr(same idx)={c_same:+.4f}  corr(control idx+1)={c_ctrl:+.4f}  identical onsets: {ident}/10000')
print('SEED-SHIFT DEFECT CONFIRMED' if ok else 'seed shift not reproduced')
