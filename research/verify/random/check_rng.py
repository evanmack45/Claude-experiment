#!/usr/bin/env python3
"""Verifier: (1) my own pure-Python splitmix64 sampling per the documented scheme vs the finder's
`randexp dump` and my mysim dump; (2) check whether any two (seed, sample_index, k, p) tuples used
across the four sweeps share an RNG state (which would make configurations non-distinct);
(3) duplicate-configuration count within the main sweep (expected for tiny boxes)."""
import subprocess, json, hashlib, itertools, csv, os
M = (1 << 64) - 1
def sm(state):
    state = (state + 0x9E3779B97F4A7C15) & M; z = state
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M
    return state, z ^ (z >> 31)
def state0(seed, idx, k, p):
    return (seed*0x9E3779B97F4A7C15 + idx*0xBF58476D1CE4E5B9 + k*0x94D049BB133111EB + int(round(1000*p))*0xD6E8FEB86659FD93) & M
def cfg(k, p, seed, idx):
    s = state0(seed, idx, k, p); xmin = -(k//2); out = []
    for i in range(k*k):
        s, r = sm(s)
        if (r >> 11) / 2.0**53 < p: out.append([xmin + i % k, xmin + i // k])
    return out
F = '/home/user/Claude-experiment/research/random'
nbad = 0; ntest = 0
for (k, p, seed, idx) in [(5, 0.1, 20260919, 0), (8, 0.9, 20260919, 9999), (64, 0.75, 20260919, 4491), (7, 0.5, 1, 3), (512, 0.5, 20260921, 9269), (32, 0.05, 20260922, 7434), (64, 0.9, 20260920, 96681)]:
    mine = cfg(k, p, seed, idx)
    a = json.loads(subprocess.check_output([F + '/randexp', 'dump', str(k), str(p), str(seed), str(idx)]))['black_cells']
    b = json.loads(subprocess.check_output(['./mysim', 'dump', str(k), str(p), str(seed), str(idx)]))['black_cells']
    ntest += 1
    if not (mine == a == b): nbad += 1; print('RNG MISMATCH', k, p, seed, idx, len(mine), len(a), len(b))
print('RNG: %d configs compared python vs randexp dump vs mysim dump, %d mismatches' % (ntest, nbad))
L = json.load(open('/home/user/Claude-experiment/research/results/random_longest.json'))
print('random_longest.json cells == my python regen:', L['black_cells'] == cfg(L['k'], L['p'], L['seed'], L['sample_index']), 'n', len(L['black_cells']), L['n_black'])
# box definition check: for k=5 cells in [-2,2]^2, for k=8 in [-4,3]^2
for k in (5, 8, 64, 512):
    c = cfg(k, 0.9, 1, 1); xs = [q[0] for q in c]; ys = [q[1] for q in c]
    print('k=%d box: x in [%d,%d] y in [%d,%d]  (expected [%d,%d])' % (k, min(xs), max(xs), min(ys), max(ys), -(k//2), -(k//2)+k-1))
# (2) state collisions across all 4,730,000 tuples
import numpy as np
A, B, C, Dd = 0x9E3779B97F4A7C15, 0xBF58476D1CE4E5B9, 0x94D049BB133111EB, 0xD6E8FEB86659FD93
tuples = []
KS = [5, 8, 12, 16, 24, 32, 48, 64]; PS = [0.1, 0.25, 0.5, 0.75, 0.9]
for k in KS:
    for p in PS:
        tuples.append((20260919, 10000, k, p)); tuples.append((20260920, 100000, k, p))
for k in [5, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512]: tuples.append((20260921, 10000, k, 0.5))
for i in range(1, 20): tuples.append((20260922, 10000, 32, i/20))
states = []
idx = np.arange(100000, dtype=np.uint64)
for (seed, n, k, p) in tuples:
    base = np.uint64(state0(seed, 0, k, p))
    st = (base + idx[:n] * np.uint64(B)) & np.uint64(M)  # wraps mod 2^64 automatically
    states.append(st)
allst = np.concatenate(states)
print('total tuples', len(allst), 'distinct RNG states', len(np.unique(allst)))
# (3) duplicate configurations inside the main sweep per cell
rows = {}
for f in ('procA.csv', 'procB.csv'):
    for r in csv.reader(open(os.path.join(F, 'out', f))): rows.setdefault((int(r[0]), float(r[1])), []).append(r)
for (k, p) in [(5, 0.1), (5, 0.5), (8, 0.1), (12, 0.1)]:
    hs = {}
    for r in rows[(k, p)]:
        h = hashlib.md5(json.dumps(cfg(k, p, 20260919, int(r[3]))).encode()).hexdigest()
        hs.setdefault(h, []).append(int(r[5]))
    dup = sum(len(v) - 1 for v in hs.values())
    incons = sum(1 for v in hs.values() if len(set(v)) > 1)
    print('cell k=%d p=%g: %d distinct configs of 10000 (%d duplicates); duplicate configs with inconsistent onset: %d' % (k, p, len(hs), dup, incons))
