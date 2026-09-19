#!/usr/bin/env python3
"""Compare my vexh records (out/k{1..4}.rec) with the finder's per-config CSVs
(research/exhaustive/out/k{1..4}_records.csv) field by field."""
import numpy as np, csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
FIND = os.path.normpath(os.path.join(HERE, "..", "..", "exhaustive", "out"))
dt = np.dtype([("s", "<u4"), ("cert", "<u4"), ("altcert", "<u4"), ("dx", "i1"), ("dy", "i1"), ("dir", "i1"), ("status", "i1")])
DIR = ["+x,+y", "+x,-y", "-x,+y", "-x,-y"]
for k in (1, 2, 3, 4):
    mine = np.fromfile(os.path.join(HERE, "out", "k%d.rec" % k), dtype=dt)
    rows = list(csv.DictReader(open(os.path.join(FIND, "k%d_records.csv" % k))))
    assert len(rows) == 2 ** (k * k) == len(mine), (len(rows), len(mine))
    nbad = 0
    for i, r in enumerate(rows):
        assert int(r["cfg"]) == i
        m = mine[i]
        ok = (int(r["status"]) == 0 == m["status"] and int(r["s"]) == m["s"] and int(r["steps"]) == m["cert"]
              and int(r["dispx"]) == m["dx"] and int(r["dispy"]) == m["dy"] and r["dir"] == DIR[m["dir"]])
        if not ok:
            nbad += 1
            if nbad <= 5: print("MISMATCH k=%d cfg=%d finder=%s mine=%s" % (k, i, r, m))
    print("k=%d: %d configs compared, %d mismatches (s, cert step, displacement, direction, status)" % (k, len(rows), nbad))
