#!/usr/bin/env python3
"""Independent statistics (min/mean/median/max/mode/log-bins) from the finder's raw hist.bin
files, to check analyze.py's arithmetic separately from the simulation."""
import numpy as np, os, json, math
F = "/home/user/Claude-experiment/research/exhaustive/out"
parts = {1: ["k1"], 2: ["k2"], 3: ["k3"], 4: ["k4"], 5: ["k5/half0", "k5/half1"]}
def stats(h):
    n = int(h.sum()); s = np.arange(h.size, dtype=np.int64)
    mean = float((h * s).sum()) / n
    # expand order statistics via cumulative counts
    cum = np.cumsum(h)
    def order(i):  # i-th smallest, 1-based
        return int(np.searchsorted(cum, i))
    med = (order(n // 2) + order(n // 2 + 1)) / 2 if n % 2 == 0 else float(order((n + 1) // 2))
    nz = np.nonzero(h)[0]
    mode = int(nz[np.argmax(h[nz])])
    return n, int(nz[0]), mean, med, int(nz[-1]), mode, int(h[mode]), int(h[nz[0]])
def logbins(h):
    edges = sorted(set(int(round(10 ** (j / 10))) for j in range(0, 71)))
    out = []
    for a, b in zip(edges, edges[1:]):
        c = int(h[a:b].sum())
        if c: out.append((a, b, c))
    return out
for k, ps in parts.items():
    h = sum(np.fromfile(os.path.join(F, p + "_hist.bin"), dtype=np.uint32).astype(np.int64) for p in ps)
    n, mn, mean, med, mx, mode, modec, minc = stats(h)
    print("k=%d n=%d min=%d(count %d) mean=%.5f median=%s max=%d mode=%d(count %d)" % (k, n, mn, minc, mean, med, mx, mode, modec))
    lb = logbins(h)
    if k == 5:
        print("  k5 modal log bin:", max(lb, key=lambda z: z[2]), " top bin:", lb[-1], " lowest bin:", lb[0])
    # compare against exact csv
    csv = np.loadtxt(os.path.join(F, "k%d_hist_exact.csv" % k), delimiter=",", skiprows=1, dtype=np.int64).reshape(-1, 2)
    ok = np.array_equal(csv[:, 0], np.nonzero(h)[0]) and np.array_equal(csv[:, 1], h[np.nonzero(h)[0]])
    print("  hist_exact.csv matches hist.bin:", ok)
