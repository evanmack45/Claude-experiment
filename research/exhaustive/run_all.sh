#!/bin/sh
# Reproduces every number in research/results/exhaustive.json from scratch.
# Usage: sh research/exhaustive/run_all.sh   (from any directory)
# Wall time: ~4 s for k<=4, ~17 min for k=5 (two processes, ~105 Msteps/s each).
set -e
cd "$(dirname "$0")"
gcc -O3 -march=native -o exhaust exhaust.c
mkdir -p out
mkdir -p out/k5
CAP=5000000
./exhaust 1 0 2      $CAP out/k1 1
./exhaust 2 0 16     $CAP out/k2 1
./exhaust 3 0 512    $CAP out/k3 1
./exhaust 4 0 65536  $CAP out/k4 1
./exhaust 5 0        16777216 $CAP out/k5/half0 0 2> out/k5/half0.log &
./exhaust 5 16777216 33554432 $CAP out/k5/half1 0 2> out/k5/half1.log &
wait
python3 naive.py 20000            # independent empty-grid check (prints s=9977)
python3 analyze.py                # merges, cross-checks vs naive.py, writes ../results/exhaustive.json
