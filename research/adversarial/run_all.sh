#!/bin/sh
# Reproduce every number in research/results/adversarial.json and adversarial_best.json.
set -e; cd "$(dirname "$0")"
mkdir -p out
gcc -O3 -march=native -Wall -o antsim antsim.c
printf '' > out/empty.cfg; printf '0 0\n' > out/origin.cfg; printf '[[-1,-1],[1,-1],[-1,0],[1,0],[-1,1],[1,1]]' > out/k3best.cfg
for f in out/empty.cfg out/origin.cfg out/k3best.cfg; do python3 verify_py.py $f 60000; done   # cross-checks (9977, 9978, 43264)
python3 attack_a.py                                     # obstacles on the road (1512 placements, <1 s)
python3 attack_c.py                                     # 203 structured seeds (<1 s)
python3 attack_b.py --seed 1 --budget 10000 --out out/attack_b_main_seed1 --lam 4 --stall 600 &          # main 20,000-eval GA, 2 processes
python3 attack_b.py --seed 2 --budget 10000 --out out/attack_b_main_seed2 --lam 4 --stall 600 --start-k5 &
wait
# extended GA (optional, ~15 min): the archived run was terminated after ~1.7M evals/process; summaries written from the flushed CSV
# python3 attack_b.py --seed 11 --budget 100000000 --time-limit 900 --out out/attack_b_ext_seed11 --lam 8 --stall 2000 &
# python3 attack_b.py --seed 12 --budget 100000000 --time-limit 900 --out out/attack_b_ext_seed12 --lam 8 --stall 2000 --start-k5 & wait
python3 aggregate_b.py                                  # -> research/results/adversarial_best.json (+ fresh antsim & Python re-verification)
python3 attack_d.py 300 40                              # greedy obstacle chaining in |x|,|y|<=300
python3 make_results.py                                 # -> research/results/adversarial.json
