#!/bin/sh
# One-command reproduction of every number in this review (~2 min, <= 2 processes).
set -e
H="$(cd "$(dirname "$0")" && pwd)"
cd "$H"; mkdir -p build out
cp "$H/../../exhaustive/exhaust.c" build/exhaust_copy.c
gcc -O3 -march=native -o build/exhaust build/exhaust_copy.c
bash test_old_vs_new_binary.sh > out/old_vs_new.txt 2>&1 &
python3 test_records_vs_indep.py            # writes out/records_check.txt
wait
python3 test_stats_from_hist.py | tee out/stats_check.txt
bash test_boundary_cap.sh | tee out/boundary_cap.txt
cat out/old_vs_new.txt
