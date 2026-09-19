#!/usr/bin/env python3
"""Verifier: certification soundness spot check. Draw a recorded-seed random subset of main-sweep samples,
re-run each with `mysim2 long` for max(10x its certification step, 200000) steps WITHOUT the certification
stop, and check that the post-hoc onset s is unchanged and that no turn mismatch t[k]!=t[k+104] occurs
after s over the whole extended run. Usage: python3 soundness.py [nsamples] [rngseed]"""
import csv, json, random, subprocess, sys, os
n = int(sys.argv[1]) if len(sys.argv) > 1 else 200; rs = int(sys.argv[2]) if len(sys.argv) > 2 else 12345
rows = []
for f in ('procA.csv', 'procB.csv'):
    rows += list(csv.reader(open('/home/user/Claude-experiment/research/random/out/' + f)))
random.seed(rs); sub = random.sample(rows, n)
bad = 0; tot_periods = 0
for r in sub:
    k, p, seed, idx, s, steps = r[0], r[1], r[2], r[3], int(r[5]), int(r[7])
    N = max(10 * steps, 200000)
    o = json.loads(subprocess.check_output(['./mysim2', 'long', k, p, seed, idx, str(N)]))
    ok = o['onset_step'] == s and o['mismatches_after_s'] == 0 and o['outcome'] in ('certified', 'nontravel', 'boundary')
    tot_periods += o['periods_verified']
    if not ok: bad += 1; print('SOUNDNESS FAIL', r[:8], o)
print('soundness: %d samples (python random.seed(%d)), extended to >=10x certification step: %d failures; total periods checked %d' % (n, rs, bad, tot_periods))
json.dump({'n': n, 'rng_seed': rs, 'failures': bad, 'total_periods_checked': tot_periods}, open('out/soundness.json', 'w'))
