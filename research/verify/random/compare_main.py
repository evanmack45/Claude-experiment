#!/usr/bin/env python3
"""Verifier: row-by-row comparison of my independent re-run (out/myA.csv, out/myB.csv) with the
finder's out/procA.csv, out/procB.csv over all 400,000 main-sweep configurations."""
import csv, os
F = '/home/user/Claude-experiment/research/random/out'; V = '/home/user/Claude-experiment/research/verify/random/out'
def load(d, names):
    out = {}
    for f in names:
        for r in csv.reader(open(os.path.join(d, f))): out[(r[0], r[1], r[2], r[3])] = r
    return out
theirs = load(F, ('procA.csv', 'procB.csv')); mine = load(V, ('myA.csv', 'myB.csv'))
print('finder rows', len(theirs), 'my rows', len(mine), 'same key set', set(theirs) == set(mine))
fields = ['outcome', 'onset_step', 'direction', 'steps_simulated', 'n_black', 'dispx', 'dispy', 'fx', 'fy', 'bx0', 'by0', 'bx1', 'by1', 'periods_verified']
mism = {f: 0 for f in fields}; nbad = 0; ex = []
for k, r in theirs.items():
    m = mine[k]; bad = False
    for i, f in enumerate(fields, start=4):
        if r[i] != m[i]: mism[f] += 1; bad = True
    if bad:
        nbad += 1
        if len(ex) < 5: ex.append((k, r[4:18], m[4:18]))
print('rows with any disagreement:', nbad, 'per-field:', mism)
for e in ex: print('example', e)
maxabs = max(int(m[18]) for m in mine.values()); maxfinal = max(max(abs(int(m[11])), abs(int(m[12]))) for m in mine.values())
print('TRUE max |coordinate| over all steps of all 400000 runs (my simulator):', maxabs, '; max |final coordinate|:', maxfinal)
print('rows with any t[k]!=t[k+104] for k>s (post-hoc full-array check):', sum(1 for m in mine.values() if m[19] != '0'))
print('my outcomes:', {o: sum(1 for m in mine.values() if m[4] == o) for o in ('certified', 'cap', 'boundary', 'nontravel')})
# where is the max |coord| attained
am = max(mine.values(), key=lambda m: int(m[18])); print('argmax maxabs row:', am)
af = max(mine.values(), key=lambda m: max(abs(int(m[11])), abs(int(m[12])))); print('argmax final row:', af)
