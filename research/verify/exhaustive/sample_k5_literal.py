#!/usr/bin/env python3
"""Random subset of k=5 configurations (seed 12345, 200 configs, python random.Random)
simulated with literal.py; writes out/k5_sample_literal.json. compare_k5.py checks them
against my C records (out/k5/h*.rec)."""
import random, json, os
from literal import analyse
HERE = os.path.dirname(os.path.abspath(__file__))
rng = random.Random(12345)
cfgs = sorted(rng.sample(range(1 << 25), 200))
def cells(cfg):
    return [(-2 + i % 5, -2 + i // 5) for i in range(25) if (cfg >> i) & 1]
res = []
for cfg in cfgs:
    N = 40000
    while True:
        r = analyse(cells(cfg), N)
        if r["cert_incl_init"] is not None and r["periods_verified"] >= 25: break
        N *= 4
    res.append(dict(cfg=cfg, s=r["s"], cert=r["cert_incl_init"], cert_mod=r["cert_modified_only"], disp=r["disp"], direction=r["direction"]))
json.dump(res, open(os.path.join(HERE, "out", "k5_sample_literal.json"), "w"), indent=0)
print("done", len(res), "configs; max s in sample =", max(r["s"] for r in res))
