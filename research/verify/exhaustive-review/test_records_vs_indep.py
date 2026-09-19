#!/usr/bin/env python3
"""Run the (freshly compiled copy of) exhaust.c on small ranges with records=1
and compare EVERY field of every record with the independent simulator.
Also compares a random sample of the finder's own out/k4_records.csv and
checks heading periodicity + footprint at certification.
Usage: python3 test_records_vs_indep.py   (writes out/records_check.txt)"""
import csv, json, os, random, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
EXH = os.path.join(HERE, "..", "..", "exhaustive")
sys.path.insert(0, HERE); import indep_sim as I
BIN = os.path.join(HERE, "build", "exhaust")

def run_c(k, lo, hi, pre):
    subprocess.run([BIN, str(k), str(lo), str(hi), "5000000", pre, "1"], check=True, stderr=subprocess.DEVNULL)
    return list(csv.DictReader(open(pre + "_records.csv")))

def compare(k, rows, label, log):
    bad = 0; n = 0; hp_fail = 0; fp_max = 0; maxabs_diff = 0
    for r in rows:
        n += 1
        cfg = int(r["cfg"]); cells = I.cells_of(k, cfg)
        assert json.loads(r["cells"]) == [list(c) for c in cells], (k, cfg, r["cells"], cells)
        N = int(r["steps"]) + 300
        a = I.analyse(cells, N)
        cres = dict(s=int(r["s"]), cert=int(r["steps"]), disp=(int(r["dispx"]), int(r["dispy"])), dir=r["dir"],
                    final=(int(r["fx"]), int(r["fy"])), bbox=tuple(int(r[c]) for c in ("bx0", "by0", "bx1", "by1")))
        ok = r["status"] == "0" and all(a[key] == cres[key] for key in cres)
        if not ok:
            bad += 1; log.write("MISMATCH %s cfg=%d C=%s indep=%s\n" % (label, cfg, cres, {kk: a[kk] for kk in cres}))
        if not a.get("heading_periodic", False): hp_fail += 1
        fp_max = max(fp_max, max(a["footprint"]))
        maxabs_diff = max(maxabs_diff, a["maxabs_upto_cert"] - max(abs(a["final"][0]), abs(a["final"][1])))
    log.write("%s: %d configs compared, %d mismatches, heading-periodicity failures=%d, max per-period footprint=%d, max(|coord| up to cert - |final coord|)=%d\n"
              % (label, n, bad, hp_fail, fp_max, maxabs_diff))
    return bad

with open(os.path.join(HERE, "out", "records_check.txt"), "w") as log:
    tot = 0
    for k, hi in ((1, 2), (2, 16), (3, 512)):
        rows = run_c(k, 0, hi, os.path.join(HERE, "out", "chk_k%d" % k))
        assert len(rows) == hi
        tot += compare(k, rows, "k=%d all %d configs (fresh binary)" % (k, hi), log)
    for lo, hi in ((31064600, 31064700), (17781200, 17781300), (5000000, 5000100), (0, 100)):
        rows = run_c(5, lo, hi, os.path.join(HERE, "out", "chk_k5_%d" % lo))
        tot += compare(5, rows, "k=5 range [%d,%d) (fresh binary)" % (lo, hi), log)
    random.seed(12345)
    rows = list(csv.DictReader(open(os.path.join(EXH, "out", "k4_records.csv"))))
    assert len(rows) == 65536
    sample = random.sample(rows, 200) + [r for r in rows if int(r["cfg"]) in (29641, 6428)]
    tot += compare(4, sample, "k=4 200 random rows + argmax/argmin of finder's out/k4_records.csv", log)
    log.write("TOTAL mismatches: %d\n" % tot)
print(open(os.path.join(HERE, "out", "records_check.txt")).read())
