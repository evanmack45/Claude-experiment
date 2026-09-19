#!/bin/sh
# Edge-case tests of exhaust.c on tiny inputs:
#  (1) cap handling / step counting: cap=100 -> steps=100 status=1(CAP)
#  (2) status classification when the cap falls between 20-periods-verified and escape
#  (3) grid-boundary handling: a copy compiled with GRID=64 must report status=2
#      (BOUNDARY) at exactly the step where the independent simulator first reaches
#      relative x<=-32, x>=31, y<=-32 or y>=31 -- no silent wrap/clip.
set -e
H="$(cd "$(dirname "$0")" && pwd)"
cd "$H"
sed 's/#define GRID 4096/#define GRID 64/' build/exhaust_copy.c > build/exhaust_g64.c
gcc -O3 -o build/exhaust_g64 build/exhaust_g64.c 2>/dev/null
echo "== (1) cap=100, empty grid"; build/exhaust 1 0 1 100 out/cap100 1 2>/dev/null; cat out/cap100_records.csv
echo "== (2) cap=12335 (one step before certification 12336; 20 periods already verified since 9977+2184=12161)"
build/exhaust 1 0 1 12335 out/cap12335 1 2>/dev/null; cat out/cap12335_records.csv; cat out/cap12335_special.txt
echo "== (2b) cap=12336"; build/exhaust 1 0 1 12336 out/cap12336 1 2>/dev/null; tail -1 out/cap12336_records.csv
echo "== (3) GRID=64 copy, k=3 all 512 configs"; build/exhaust_g64 3 0 512 5000000 out/g64_k3 1 2>/dev/null
python3 - <<'PY'
import csv, sys
sys.path.insert(0, "."); import indep_sim as I
rows = list(csv.DictReader(open("out/g64_k3_records.csv")))
nb = 0; bad = 0; ncert = 0
for r in rows:
    cfg = int(r["cfg"]); cells = I.cells_of(3, cfg)
    if r["status"] == "2":
        nb += 1
        turns, pos, head, fm, ma = I.simulate(cells, int(r["steps"]) + 10)
        first = next(n for n, (x, y) in enumerate(pos) if x <= -32 or x >= 31 or y <= -32 or y >= 31)
        if first != int(r["steps"]) or (int(r["fx"]), int(r["fy"])) != pos[first]: bad += 1; print("BAD", r, first, pos[first])
    else:
        ncert += 1
print("GRID=64: %d boundary runs, %d certified, %d inconsistent with independent sim (expect 0)" % (nb, ncert, bad))
PY
grep -o '"n_boundary": [0-9]*' out/g64_k3_summary.txt
