#!/bin/sh
# Verifier's full re-run of the finder's main sweep with the independent simulator mysim (2 processes).
set -e
D="$(cd "$(dirname "$0")" && pwd)"
cd "$D"
gcc -O3 -march=native -o mysim mysim.c -lm
rm -f out/myA.csv out/myB.csv
(for k in 5 12 24 48; do for p in 0.1 0.25 0.5 0.75 0.9; do ./mysim run $k $p 20260919 10000 20000000 out/myA.csv; done; done; echo A_DONE) > out/myA.log 2>&1 &
(for k in 8 16 32 64; do for p in 0.1 0.25 0.5 0.75 0.9; do ./mysim run $k $p 20260919 10000 20000000 out/myB.csv; done; done; echo B_DONE) > out/myB.log 2>&1 &
wait
echo MAIN_DONE
