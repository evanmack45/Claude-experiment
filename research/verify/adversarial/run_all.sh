#!/bin/sh
# Reproduce every number in the verify/adversarial verdicts (about 2-3 min; the finder's antsim must exist).
set -e; cd "$(dirname "$0")"
gcc -O2 -o vsim vsim.c
printf '' > out/empty.cfg; printf '0 0\n' > out/origin.cfg
printf -- '-1 -1\n1 -1\n-1 0\n1 0\n-1 1\n1 1\n' > out/k3best.cfg
printf -- '-2 -2\n1 -2\n0 -1\n1 -1\n-2 0\n-1 0\n-2 1\n-1 1\n0 1\n' > out/k4best.cfg
printf -- '0 -2\n2 -2\n-2 -1\n-1 -1\n2 -1\n0 1\n2 1\n-2 2\n0 2\n1 2\n2 2\n' > out/k5best.cfg
for f in empty origin k3best k4best k5best; do ./vsim run out/$f.cfg; done            # C10 references
./vsim run ../../adversarial/out/attack_b_best.cfg                                       # C2
./vsim run ../../adversarial/out/attack_d_final.cfg                                      # C3
python3 pyref.py out/empty.cfg 13000; python3 pyref.py out/origin.cfg 13000; python3 pyref.py out/k3best.cfg 47000   # pure-Python (no C) cross-check
python3 check_a.py            # C4, C5, C6 (all 1512 placements regenerated + re-simulated)
python3 check_c.py            # C9  (all 203 configs re-simulated)
python3 check_d.py            # C3  (greedy chaining re-implemented)
python3 check_b_csv.py 1500   # C7, C8 (CSV statistics + seeded 1500-row samples)
python3 check_b_full.py       # C1, C7, C8 (all 20,000 main rows + 2 x 20,000 ext rows re-simulated)
python3 check_distinct.py     # C1 (distinct configurations vs. logged evaluations)
# C7 determinism: re-run the finder's GA into out/b_rerun and byte-compare with the archived CSVs
mkdir -p out/b_rerun; ( cd ../../adversarial && python3 attack_b.py --seed 1 --budget 10000 --out ../verify/adversarial/out/b_rerun/seed1 --lam 4 --stall 600 >/dev/null 2>&1 )
( cd ../../adversarial && python3 attack_b.py --seed 2 --budget 10000 --out ../verify/adversarial/out/b_rerun/seed2 --lam 4 --stall 600 --start-k5 >/dev/null 2>&1 )
cmp out/b_rerun/seed1.csv ../../adversarial/out/attack_b_main_seed1.csv && cmp out/b_rerun/seed2.csv ../../adversarial/out/attack_b_main_seed2.csv && echo "main GA CSVs byte-identical"
# C11: finder's cap-rerun policy and outcome-branch sanity tests
( cd ../../adversarial && ./rerun_cap.sh out/k3best.cfg && ./antsim run out/empty.cfg --cap 5000 && ./antsim run out/empty.cfg --cap 12200 && ./antsim run out/empty.cfg --cap 5000 --grid 32 )
