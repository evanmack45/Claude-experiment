#!/usr/bin/env python3
"""Verifier: recompute the aggregate claims (C1, C4, C5, C6, C7, C10, C11, C12) directly from the
finder's raw outputs (procA/procB.csv, results/random_samples.csv, out/*/ *.u32) with my own code
(numpy only for lstsq; medians/percentiles by explicit sorting)."""
import csv, json, glob, os, math
import numpy as np
F = '/home/user/Claude-experiment/research/random'
R = '/home/user/Claude-experiment/research/results'
rows = []
for f in ('procA.csv', 'procB.csv'):
    for r in csv.reader(open(os.path.join(F, 'out', f))):
        rows.append(r)
print('raw rows', len(rows), 'ncols set', {len(r) for r in rows})
# compare with results/random_samples.csv
pub = list(csv.reader(open(os.path.join(R, 'random_samples.csv'))))
hdr, pub = pub[0], pub[1:]
print('published header', hdr, 'rows', len(pub))
key8 = sorted(tuple(r[:8]) for r in rows); pub8 = sorted(tuple(r) for r in pub)
print('published csv == raw first 8 cols (as multiset):', key8 == pub8)
outc = {}
for r in rows: outc[r[4]] = outc.get(r[4], 0) + 1
print('outcomes', outc)
cells = {}
for r in rows: cells.setdefault((int(r[0]), float(r[1])), []).append(r)
print('cells', len(cells), 'sizes', sorted({len(v) for v in cells.values()}), 'seeds', {r[2] for r in rows})
for c, v in cells.items():
    assert len({r[3] for r in v}) == 10000 and set(int(r[3]) for r in v) == set(range(10000)), c
print('every cell has sample_index 0..9999 exactly once: True')
def median(a):
    a = sorted(a); n = len(a)
    return a[n//2] if n % 2 else (a[n//2-1] + a[n//2]) / 2
S = [int(r[5]) for r in rows]
print('C4: min %d median %s mean %.4f max %d frac<9977 %.7f n=%d' % (min(S), median(S), sum(S)/len(S), max(S), sum(1 for s in S if s < 9977)/len(S), len(S)))
# C5/C6 medians at p=0.5
KS = [5, 8, 12, 16, 24, 32, 48, 64]
med05 = [median([int(r[5]) for r in cells[(k, 0.5)]]) for k in KS]
print('C5: medians p=0.5', med05, 'monotone', all(a < b for a, b in zip(med05, med05[1:])))
def fit(xs, ys):
    lx, ly = np.log(np.array(xs, float)), np.log(np.array(ys, float))
    A = np.vstack([np.ones_like(lx), lx]).T
    coef = np.linalg.lstsq(A, ly, rcond=None)[0]
    pred = A @ coef; r2 = 1 - ((ly-pred)**2).sum() / ((ly-ly.mean())**2).sum()
    # closed form check
    b = ((lx-lx.mean())*(ly-ly.mean())).sum() / ((lx-lx.mean())**2).sum()
    return coef[1], r2, b
e_all = fit(KS, med05); e_ge24 = fit(KS[4:], med05[4:])
print('C6: exponent all k %.4f r2 %.4f (closed-form b %.4f); k>=24 %.4f r2 %.4f' % (e_all[0], e_all[1], e_all[2], e_ge24[0], e_ge24[1]))
# C10
cert = [r for r in rows if r[4] == 'certified']
nd = sum(1 for r in cert if abs(int(r[9])) != 2 or abs(int(r[10])) != 2)
dc = {}
for r in cert: dc[r[6]] = dc.get(r[6], 0) + 1
print('C10: n_disp_not_pm2_pm2', nd, 'dir counts', dc, 'sum', sum(dc.values()))
# direction consistent with disp sign?
bad = sum(1 for r in cert if r[6] != ('+x' if int(r[9]) > 0 else '-x') + ',' + ('+y' if int(r[10]) > 0 else '-y'))
print('C10: rows where direction label disagrees with sign of disp:', bad)
# C11
print('C11: max steps_simulated', max(int(r[7]) for r in rows), 'max |final coord|', max(max(abs(int(r[11])), abs(int(r[12]))) for r in rows),
      'max |bbox corner| (pre-onset)', max(max(abs(int(r[i])) for i in (13, 14, 15, 16)) for r in rows),
      'max over final+bbox', max(max(abs(int(r[i])) for i in (11, 12, 13, 14, 15, 16)) for r in rows))
print('C11: periods_verified min', min(int(r[17]) for r in cert), 'max', max(int(r[17]) for r in cert))
# certification consistency: steps_simulated >= onset + 2184 for all?
print('rows with steps_simulated < onset+2184:', sum(1 for r in cert if int(r[7]) < int(r[5]) + 2184))
# margin check from recorded final pos + bbox
badm = 0
for r in cert:
    fx, fy, bx0, by0, bx1, by1, dx, dy = (int(r[i]) for i in (11, 12, 13, 14, 15, 16, 9, 10))
    okx = fx >= bx1 + 20 if dx > 0 else fx <= bx0 - 20
    oky = fy >= by1 + 20 if dy > 0 else fy <= by0 - 20
    if not (okx and oky): badm += 1
print('rows whose recorded final position violates the 20-cell margin:', badm)
# n_black vs binomial expectation per cell
for (k, p), v in sorted(cells.items()):
    nb = [int(r[8]) for r in v]; m = sum(nb)/len(nb); exp = k*k*p; sd = math.sqrt(k*k*p*(1-p)/len(nb))
    z = (m-exp)/sd
    if abs(z) > 3: print('n_black z-score > 3 at', k, p, z)
print('n_black per-cell means all within 3 sigma of k^2 p (printed above if not)')
# C7 and C12 from u32 files (finder's raw aggregate outputs)
def load(sub):
    out = {}
    for fn in sorted(glob.glob(os.path.join(F, 'out', sub, '*.u32'))):
        a = np.fromfile(fn, dtype=np.uint32).astype(np.int64).tolist()
        base = os.path.basename(fn)[:-4]
        out[base] = a
    return out
sc = load('scale')
ks = sorted(int(b[1:]) for b in sc)
meds = [median(sc['k%d' % k]) for k in ks]; ns = [len(sc['k%d' % k]) for k in ks]
print('C7: scale k', ks); print('    n', ns); print('    medians', meds)
print('    max', [max(sc['k%d' % k]) for k in ks])
big = [k for k in ks if k >= 64]; bm = [m for k, m in zip(ks, meds) if k >= 64]
e = fit(big, bm); eN = fit([k*k*0.5 for k in big], bm)
print('C7: exponent k>=64 in k %.4f r2 %.4f ; in N=k^2 p %.4f' % (e[0], e[1], eN[0]))
# using actual mean n_black as finder did
summ = {}
for fn in glob.glob(os.path.join(F, 'out', 'scale', '*_summary.jsonl')):
    for line in open(fn):
        s = json.loads(line); summ[s['k']] = s
eN2 = fit([summ[k]['mean_n_black'] for k in big], bm)
print('C7: exponent in N using recorded mean_n_black %.4f' % eN2[0])
pf = load('pfine')
ps = sorted(float(b[1:]) for b in pf)
print('C12: pfine p', ps); print('     n', [len(pf['p%g' % p]) for p in ps]); print('     medians', [median(pf['p%g' % p]) for p in ps])
ext = load('ext')
print('ext: cells', len(ext), 'total n', sum(len(v) for v in ext.values()), 'max onset', max(max(v) for v in ext.values()),
      'argmax cell', max(ext, key=lambda b: max(ext[b])))
b = max(ext, key=lambda b: max(ext[b])); a = ext[b]; print('     argmax index', a.index(max(a)))
print('grand total (rows + ext + scale + pfine):', len(rows) + sum(len(v) for v in ext.values()) + sum(ns) + sum(len(v) for v in pf.values()))
