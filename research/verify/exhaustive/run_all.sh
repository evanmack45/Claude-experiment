#!/bin/sh
set -e
D=/home/user/Claude-experiment/research/verify/exhaustive
cd "$D"; mkdir -p out/k5
gcc -O3 -march=native -Wno-misleading-indentation -o vexh vexh.c
./vexh 1 0 2 5000000 out/k1; ./vexh 2 0 16 5000000 out/k2; ./vexh 3 0 512 5000000 out/k3; ./vexh 4 0 65536 5000000 out/k4
./vexh 5 0 16777216 5000000 out/k5/h0 2> out/k5/h0.log &
./vexh 5 16777216 33554432 5000000 out/k5/h1 2> out/k5/h1.log &
wait
python3 compare_small.py
python3 sample_k5_literal.py
python3 compare_k5.py | tee out/compare_k5.log
python3 stats_from_finder_hist.py | tee out/stats_from_finder_hist.log
python3 literal.py 20000 | tee out/literal_empty.log
python3 footprint.py | tee out/footprint.log
