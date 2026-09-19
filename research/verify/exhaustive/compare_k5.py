#!/usr/bin/env python3
"""Compare my full k=5 enumeration (out/k5/h0.rec, h1.rec) with the finder's outputs."""
import numpy as np, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "exhaustive", "out", "k5")
dt = np.dtype([("s", "<u4"), ("cert", "<u4"), ("altcert", "<u4"), ("dx", "i1"), ("dy", "i1"), ("dir", "i1"), ("status", "i1")])
CAP = 5000000
h0 = np.fromfile(os.path.join(HERE, "out/k5/h0.rec"), dtype=dt); h1 = np.fromfile(os.path.join(HERE, "out/k5/h1.rec"), dtype=dt)
assert h0.size == h1.size == 1 << 24, (h0.size, h1.size)
mine = np.concatenate([h0, h1])
print("n configs:", mine.size)
print("status counts (0=cert,1=cap,2=bound,3=nontravel):", np.bincount(mine["status"].astype(np.int64), minlength=4).tolist())
s = mine["s"].astype(np.int64)
myhist = np.bincount(s, minlength=CAP + 1)
fh0 = np.fromfile(os.path.join(F, "half0_hist.bin"), dtype=np.uint32).astype(np.int64)
fh1 = np.fromfile(os.path.join(F, "half1_hist.bin"), dtype=np.uint32).astype(np.int64)
print("half0 hist identical:", np.array_equal(np.bincount(h0["s"].astype(np.int64), minlength=CAP + 1), fh0))
print("half1 hist identical:", np.array_equal(np.bincount(h1["s"].astype(np.int64), minlength=CAP + 1), fh1))
print("full hist identical:", np.array_equal(myhist, fh0 + fh1))
print("s: min=%d (count %d) max=%d mean=%.5f" % (s.min(), (s == s.min()).sum(), s.max(), s.mean()))
ss = np.sort(s); n = ss.size
print("median (mean of two middle order stats):", (int(ss[n // 2 - 1]) + int(ss[n // 2])) / 2, "lower/upper:", int(ss[n // 2 - 1]), int(ss[n // 2]))
nz = np.nonzero(myhist)[0]; mode = int(nz[np.argmax(myhist[nz])])
print("mode s=%d count=%d" % (mode, myhist[mode]))
print("argmax cfg(s):", np.nonzero(s == s.max())[0].tolist(), " argmin cfg(s):", np.nonzero(s == s.min())[0].tolist())
for c in np.nonzero(s == s.max())[0].tolist() + np.nonzero(s == s.min())[0].tolist():
    r = mine[c]; print("  cfg %d: s=%d cert=%d altcert=%d disp=(%d,%d) dir=%d cells=%s" % (c, r["s"], r["cert"], r["altcert"], r["dx"], r["dy"], r["dir"],
        [(-2 + i % 5, -2 + i // 5) for i in range(25) if (c >> i) & 1]))
print("dir counts (+x+y,+x-y,-x+y,-x-y):", np.bincount(mine["dir"].astype(np.int64), minlength=4).tolist())
print("dir counts half0:", np.bincount(h0["dir"].astype(np.int64), minlength=4).tolist(), "half1:", np.bincount(h1["dir"].astype(np.int64), minlength=4).tolist())
cert = mine["cert"].astype(np.int64)
print("total steps:", int(cert.sum()), " half0:", int(h0["cert"].astype(np.int64).sum()), " half1:", int(h1["cert"].astype(np.int64).sum()))
print("max steps any run:", int(cert.max()), "at cfg", int(np.argmax(cert)))
print("disp components all +-2:", bool((np.abs(mine["dx"]) == 2).all() and (np.abs(mine["dy"]) == 2).all()))
print("n configs where altcert (bbox without unvisited initial cells) != cert:", int((mine["altcert"] != mine["cert"]).sum()))
# log bins
edges = sorted(set(int(round(10 ** (j / 10))) for j in range(0, 71)))
lb = [(a, b, int(myhist[a:b].sum())) for a, b in zip(edges, edges[1:]) if myhist[a:b].sum()]
print("modal log bin:", max(lb, key=lambda z: z[2]), " top bin:", lb[-1], " number of nonempty bins:", len(lb))
fin = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "results", "exhaustive.json")))["results"]["k5"]["histogram_log_bins"]
print("log bins identical to finder JSON:", [(b["lo"], b["hi"], b["count"]) for b in fin] == lb)
# literal python sample
samp = json.load(open(os.path.join(HERE, "out/k5_sample_literal.json")))
bad = [x for x in samp if not (mine[x["cfg"]]["s"] == x["s"] and mine[x["cfg"]]["cert"] == x["cert"] and [int(mine[x["cfg"]]["dx"]), int(mine[x["cfg"]]["dy"])] == list(x["disp"]))]
print("literal-Python sample: %d configs, %d disagree with my C" % (len(samp), len(bad)))
for f in ("h0", "h1"): print(open(os.path.join(HERE, "out/k5/%s.sum" % f)).read().strip())
