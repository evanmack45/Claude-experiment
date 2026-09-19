#!/usr/bin/env python3
"""Recompute every statistic in claims C7/C8/C9/C10/C11 directly from the raw
hist.bin / summary files with code independent of analyze.py."""
import json, os, numpy as np
E = "/home/user/Claude-experiment/research/exhaustive/out"
J = json.load(open("/home/user/Claude-experiment/research/results/exhaustive.json"))
parts = {1: ["k1"], 2: ["k2"], 3: ["k3"], 4: ["k4"], 5: ["k5/half0", "k5/half1"]}
expect = {1: (9977, 9977.5, 9977.5, 9978), 2: (275, 7234.06, 9976.5, 11386), 3: (200, 4327.80, 2374.5, 43264),
          4: (155, 3797.99, 1736.5, 119673), 5: (32, 4250.45, 2059.0, 233232)}
claimed_dirs = {1: (0,1,0,1), 2: (4,5,3,4), 3: (138,125,117,132), 4: (16248,16430,16372,16486), 5: (8428157,8346625,8333103,8446547)}
ok = True
for k, ps in parts.items():
    h = sum(np.fromfile(os.path.join(E, p + "_hist.bin"), dtype=np.uint32).astype(np.int64) for p in ps)
    summ = [json.load(open(os.path.join(E, p + "_summary.txt"))) for p in ps]
    n = int(h.sum()); assert n == 2 ** (k * k), (k, n)
    vals = np.repeat(np.arange(h.size), h) if k < 5 else None
    s = np.arange(h.size); mean = float((h * s).sum()) / n
    cum = np.cumsum(h)
    def order(i):  # i-th order statistic, 1-based
        return int(np.searchsorted(cum, i))
    med = (order(n // 2) + order(n // 2 + 1)) / 2
    nz = np.nonzero(h)[0]; smin, smax = int(nz[0]), int(nz[-1])
    if vals is not None:
        assert abs(float(np.median(vals)) - med) < 1e-9 and abs(float(vals.mean()) - mean) < 1e-9
    assert sum(x["s_sum"] for x in summ) == (h * s).sum()
    e = expect[k]
    line = "k%d: min=%d mean=%.4f median=%s max=%d  (claim: %s) n_min_ties=%d mode=%d(%d)" % (
        k, smin, mean, med, smax, e, int(h[smin]), int(nz[np.argmax(h[nz])]), int(h[nz].max()))
    good = smin == e[0] and abs(mean - e[1]) < 0.005 and med == e[2] and smax == e[3]
    dsum = [0, 0, 0, 0]
    for x in summ:
        for i, d in enumerate(("+x,+y", "+x,-y", "-x,+y", "-x,-y")): dsum[i] += x["dir_counts"][d]
    good &= tuple(dsum) == claimed_dirs[k] and sum(dsum) == n
    good &= sum(x["n_certified"] for x in summ) == n and sum(x["n_cap"] + x["n_boundary"] + x["n_nontraveling_periodic"] for x in summ) == 0
    print(line, "dirs=%s" % dsum, "OK" if good else "FAIL"); ok &= good
    if k == 5:
        edges = [0] + sorted(set(int(round(10 ** (j / 10))) for j in range(0, 71)))
        cnt = lambda e_: int(cum[min(e_, h.size) - 1]) if e_ > 0 else 0
        b1 = cnt(3162) - cnt(2512); b2 = cnt(251189) - cnt(199526)
        modal = max(((edges[i], edges[i+1], cnt(edges[i+1]) - cnt(edges[i])) for i in range(len(edges)-1)), key=lambda t: t[2])
        print("k5 log bins: [2512,3162)=%d (claim 2329415) modal=%s [199526,251189)=%d (claim 11) exact mode s=%d count=%d (claim 266/88090); JSON bins sum=%d" % (
            b1, modal, b2, int(nz[np.argmax(h[nz])]), int(h[nz].max()), sum(b["count"] for b in J["results"]["k5"]["histogram_log_bins"])))
        ok &= b1 == 2329415 and b2 == 11 and modal[0] == 2512
        ts = sum(x["total_steps"] for x in summ); print("k5 total steps=%d (claim 216439582470) elapsed=%s msteps=%s max_cert_steps=%s max_abs_coord=%s" % (
            ts, [x["elapsed_s"] for x in summ], [x["msteps_per_s"] for x in summ], [x["max_cert_steps"] for x in summ], [x["max_abs_coord"] for x in summ]))
        ok &= ts == 216439582470
print("ALL STATS OK" if ok else "SOME STATS FAILED")
