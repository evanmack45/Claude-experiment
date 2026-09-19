#!/bin/sh
# simulation part only of run_all.sh
set -e
cd "$(dirname "$0")"
gcc -O3 -march=native -Wall -o randexp randexp.c -lm
mkdir -p out
SEED=20260919
N=10000
CAP=20000000
rm -f out/procA.csv out/procB.csv out/procA.log out/procB.log
(for k in 5 12 24 48; do for p in 0.1 0.25 0.5 0.75 0.9; do ./randexp run $k $p $SEED $N $CAP out/procA.csv; done; done) 2> out/procA.log &
(for k in 8 16 32 64; do for p in 0.1 0.25 0.5 0.75 0.9; do ./randexp run $k $p $SEED $N $CAP out/procB.csv; done; done) 2> out/procB.log &
wait
echo SIM_DONE
