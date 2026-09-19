#!/bin/sh
# Strict-certificate pass over every configuration in the 1x1..5x5 boxes (see exhaust.c header
# and README.md "Strict certificate"). Writes out/strict/*, then compare_strict.py checks that the
# strict onset histograms are bit-identical to the default ones and writes
# ../results/exhaustive_strict.json. Wall time ~17 min for k=5 on two cores.
set -e
cd "$(dirname "$0")"
gcc -O3 -march=native -o exhaust exhaust.c
mkdir -p out/strict/k5
CAP=5000000
KMAX=${K_MAX:-5}          # K_MAX=4 sh run_strict.sh : quick check without the 16-minute k=5 pass
./exhaust 1 0 2      $CAP out/strict/k1 1 1
./exhaust 2 0 16     $CAP out/strict/k2 1 1
./exhaust 3 0 512    $CAP out/strict/k3 1 1
./exhaust 4 0 65536  $CAP out/strict/k4 1 1
if [ "$KMAX" -ge 5 ]; then
./exhaust 5 0        16777216 $CAP out/strict/k5/half0 0 1 2> out/strict/k5/half0.log &
./exhaust 5 16777216 33554432 $CAP out/strict/k5/half1 0 1 2> out/strict/k5/half1.log &
wait
python3 compare_strict.py            # exits 1 if any comparison fails
else
python3 compare_strict.py --ks 1,2,3,4 --result out/strict/exhaustive_strict_k1-4.json
fi
