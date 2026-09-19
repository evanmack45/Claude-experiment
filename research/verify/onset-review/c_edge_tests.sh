#!/bin/sh
# Tiny-input and sanitizer tests of research/onset/ant.c. Usage: sh c_edge_tests.sh
# Expected: -Wall -Wextra clean; N=200/12000 ASAN clean; N=10 ASAN SEGV at ant.c:102 (PX[N-104] negative index,
# latent bug for N<104 only); N=200000 rerun bit-identical to research/onset/out/.
set -e
D=$(cd "$(dirname "$0")" && pwd); O=$D/../../onset; W=$D/work; mkdir -p $W
gcc -O2 -Wall -Wextra -o $W/ant $O/ant.c -lm && echo "compile: clean"
gcc -O1 -g -fsanitize=address -o $W/ant_asan $O/ant.c -lm
for n in 10 200 12000; do mkdir -p $W/a$n; if $W/ant_asan $n $W/a$n >$W/a$n/log 2>&1; then echo "ASAN N=$n: clean"; else echo "ASAN N=$n: $(grep -m1 -E 'ERROR' $W/a$n/log) at $(grep -m1 -oE 'ant.c:[0-9]+' $W/a$n/log)"; fi; done
mkdir -p $W/o10 $W/o200000
$W/ant 10 $W/o10 2>/dev/null; echo "N=10 turns: $(cat $W/o10/turns.txt) (expected RRRRLRRRRL)"; echo "N=10 traj: $(tr '\n' ';' < $W/o10/traj.txt)"
$W/ant 200000 $W/o200000 2>/dev/null
cmp $W/o200000/turns.txt $O/out/turns.txt && cmp $W/o200000/traj.txt $O/out/traj.txt && diff $W/o200000/onset.txt $O/out/onset.txt && echo "N=200000 rerun: bit-identical to research/onset/out"
