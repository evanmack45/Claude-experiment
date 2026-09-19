#!/usr/bin/env python3
"""Count distinct initial configurations among the random draws of every sweep for small boxes.

Regenerates the draws with the pure-Python copy of randexp.c's sampler (verify_py.gen_config)
and counts distinct patterns per box size. Draws are independent Bernoulli(p) samples, so in
small boxes many draws coincide; the sweep totals in random.json count draws (runs), not distinct
patterns. Usage: python3 count_distinct.py [k ...]   (default: 5 8; ~1 min)
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_py import gen_config

SWEEPS = [("main", 20260919, 10000, (0.1, 0.25, 0.5, 0.75, 0.9)),
          ("ext", 20260920, 100000, (0.1, 0.25, 0.5, 0.75, 0.9)),
          ("scale", 20260921, 10000, (0.5,))]
ks = [int(a) for a in sys.argv[1:]] or [5, 8]
t0 = time.time()
for k in ks:
    seen = set(); n = 0
    for name, seed, ns, ps in SWEEPS:
        for p in ps:
            for i in range(ns):
                seen.add(frozenset(map(tuple, gen_config(k, p, seed, i)))); n += 1
    print(f"k={k}: {n} draws, {len(seen)} distinct patterns, {n - len(seen)} repeats ({time.time() - t0:.0f}s)")
