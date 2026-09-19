# adversarial — trying to break the highway conjecture (Langton's ant)

All definitions follow `research/CONVENTIONS.md` (ant at (0,0) facing N, white->R, black->L,
onset step s = max{k : t[k] != t[k+104]}, certification = 20 periods AND escape margin >= 20 in both
coordinates beyond the bbox of {origin, initial black cells, cells modified in steps 1..s}).

## Reproduce everything with one command

    cd research/adversarial && ./run_all.sh

(about 30 s; the optional extended GA lines in `run_all.sh` take 15 min on 2 cores).
Outputs: `research/results/adversarial.json`, `research/results/adversarial_best.json`, raw per-run data in `out/`.

## Tool

    gcc -O3 -march=native -o antsim antsim.c
    ./antsim run <cfgfile> [--cap 50000000] [--grid 8192] [--log-every M] [--dump-final F]
    ./antsim batch [--cap N] [--grid G]      # one configuration per stdin line, one JSON result line each

Config file = black cells as "x y" lines or a JSON list. Prints outcome (certified | cap | nontravel | boundary),
onset_step, direction, disp, cert_step, first_initial_black_read (obstacle contact step), bounding boxes.
Cross-checks: reproduces onset.json (9977), the exhaustive maxima for k=1,3,5 (9978, 43264, 233232), and the
independent pure-Python `verify_py.py` agrees on every configuration it was run on (`python3 verify_py.py cfg nsteps`).
`./rerun_cap.sh cfg` is the step-5 policy (cap 500,000,000, grid 32768, log every 10M steps) — never needed.

## Results (every configuration certified; nothing ever hit the cap)

| attack | configs | non-certified | longest onset | file |
|---|---|---|---|---|
| A obstacle on the road (6 shapes x 14 distances x 9 lateral x 2 phases) | 1512 | 0 | 190600 (L3, 377 periods ahead; extra chaos after contact 138873) | `out/attack_a.jsonl` |
| B (1+lambda) GA, 12x12 box, main run 2 x 10,000 evals | 20000 | 0 | 233232 (= the k=5 exhaustive maximum, used as seed-2 start; best purely random-start: 129303) | `out/attack_b_main_seed*.csv` |
| B extended, 2 x ~1.7M evals (terminated early) | 3463028 | 0 | 233232 (seed 12, from k5 start); 206374 purely random start (seed 11) | `out/attack_b_ext_seed*.csv` |
| C structured seeds (squares, hollow squares, lines, checkerboards, crosses, ...) | 203 | 0 | 43621 (concentric_rings_13) excluding the reference k4/k5 configs | `out/attack_c.jsonl` |
| D greedy 2x2-obstacle chaining in |x|,|y|<=300 | 145 | 0 | **259274** (4 obstacles, 16 cells) = 25.99 x 9977 | `out/attack_d.jsonl`, `out/attack_d_final.cfg` |

Attack A: 616 placements actually hit the highway, 896 missed (all misses: onset exactly 9977). Every hit re-formed a
certified highway (direction re-randomised: +x,-y 238, -x,-y 264, -x,+y 85, +x,+y 29). Extra chaos after contact:
median 5012, mean 10883, p90 26156, max 138873; 63.6 % of hits re-form faster than the empty grid's 9977.

Longest onset in a bounded 12x12 box: 233232 (`research/results/adversarial_best.json`), ratio 23.38 to the empty grid.
Longest onset found overall (bounded 601x601 box, attack D): 259274, ratio 25.99.

## Definitional choices
- Onset per CONVENTIONS.md (periodic from step s+1); the "from step s inclusive" reading adds 1 to every number.
- Attack-A anchor: P0 = ant position after step 12680 (first period start after the escape margin is permanent),
  anchor = P0 + m(-2,-2) + dv(1,-1) - ph(1,1); obstacle's lower-left cell at the anchor; simulated from scratch on an empty grid.
- GA fitness of a non-certified run = 1e18 (never occurred).
- The extended GA processes were stopped by SIGTERM at ~270 s of their 900 s limit (harness deadline); their statistics
  are over the flushed portion of the CSV logs (1,742,445 and 1,720,583 evaluations), as recorded in their `_summary.json`.
