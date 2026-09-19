# verify/adversarial — independent verification of research/adversarial

Skeptical re-derivation of every numeric claim in `research/results/adversarial.json` and
`adversarial_best.json`, with code written from `research/CONVENTIONS.md` only (nothing copied from the finder).

## Reproduce every number with one command

    cd research/verify/adversarial && ./run_all.sh        # ~4 min on 1-2 cores

## Tools written here
- `vsim.c` — independent C simulator. Different design from the finder's `antsim.c`: it stores the complete turn
  sequence and position sequence and computes the onset (max k with t[k]!=t[k+104]) and the certification
  (>= 20 verified periods AND >= 20-cell escape margin beyond the bbox of origin + initial black cells + cells
  read in steps 1..s, in both coordinates of the travel direction) by full post-hoc rescans every 2048 steps.
  `./vsim run cfg | ./vsim batch` (stdin: one config per line as x y pairs). Default cap 2^23 steps.
- `pyref.py` — pure-Python reference (no C at all) for the same definitions, used on the small reference cases.
- `check_a.py` — regenerates the 1512 Attack-A placements from the stated rule with its own empty-grid simulation,
  compares the cell lists with the finder's `attack_a.jsonl`, re-simulates all 1512 and recomputes all statistics.
- `check_c.py` — re-simulates all 203 Attack-C configs; regenerates six named families independently.
- `check_d.py` — re-implements the Attack-D greedy 2x2 chaining (35 candidates/stage, box 300) from scratch.
- `check_b_csv.py`, `check_b_full.py` — CSV statistics of all four GA logs; exact re-simulation of all 20,000
  main-run rows and 2 x 20,000 seeded-sample rows (seed 777) of the extended logs, plus 4 x 1,500 rows (seed 20260919).
- `check_distinct.py` — distinct configurations vs. logged evaluations (memory-light, keyed by genome hex).
- `out/b_rerun/` — a fresh run of the finder's own `attack_b.py` (seeds 1, 2): byte-identical to the archived CSVs.

## Findings (all numbers from the commands in run_all.sh)
| claim | verdict | evidence |
|---|---|---|
| C10 references | confirmed | vsim + pyref: empty 9977 (-x,-y, cert 12336), origin 9978 (cert 12337), k3 43264 (cert 46248), k4 119673, k5 233232 (cert 235418) |
| C2 12x12 best | confirmed | vsim on `attack_b_best.cfg`: 233232, +x,-y, 11 cells, cert 235418; 233232/9977 = 23.377 |
| C3 attack D | confirmed | independent greedy re-implementation reproduces all 4 stages (35 cands each, same obstacles, onsets 51033/145886/187236/259274), final 259274 -x,-y 16 cells, cert 276869; 146 simulations |
| C4/C5/C6 attack A | confirmed | 1512/1512 identical placements; 0 per-placement mismatches (onset, contact, direction); 616 hits / 896 misses (all 9977); dirs 238/264/85/29; extra chaos min 564 median 5012 mean 10882.69 p90 26156 max 138873; 63.64% < 9977; longest 190600 = 51727 + 138873, cert 192954. Caveat: contact < 12680+104m for every hit (the period's cells run ahead of the period-start point), so the "trivial" bound is only observed for the onset, not guaranteed by contact time |
| C7 main GA | confirmed | 10,000 rows each, 0 non-certified, max 129303 (eval 5295) / 233232 (eval 1), mean 6648.75 / 7544.13; all 20,000 rows re-simulated with vsim: 0 mismatches; fresh re-run of attack_b.py byte-identical |
| C8 ext GA | confirmed | 1,742,445 / 1,720,583 rows, eval ids contiguous, 0 non-certified, max 206374 (eval 1036283, restart 311) / 233232 (eval 1); 20,000 + 1,500 sampled rows per log re-simulated: 0 mismatches; logs end at 270 s |
| C9 attack C | confirmed (note) | 0 mismatches over 203; longest non-reference concentric_rings_13 43621, then filled_square_30 31493, diamond_5 30055, vline_21 24928; filled_square_4 22116; single_1_-1 19375. Note: only 202 distinct configs (hollow_square_3 == ring8) |
| C11 cap policy | confirmed | `rerun_cap.sh out/k3best.cfg` -> certified 43264 at 46248 (cap 5e8, grid 32768); branches cap/nontravel/boundary reproduce exactly; 0 non-certified anywhere |
| C1 total | partially confirmed | 0 non-certified confirmed (every A, C, D run and 60,000 B rows re-simulated exactly; all 3,483,028 B outcome fields read). But 3,484,889 counts logged *evaluations*, not configurations: the B logs contain 806,799 duplicate genomes (2,676,229 distinct); the union of distinct configs over A, C, all B logs and the D chain is 2,677,946 (+ at most 140 unlogged D candidates); attack C has 202 distinct configs; README says D = 145 while the JSON counts 146 (the final re-simulation duplicates the stage-4 evaluation) |

Code-inspection notes on `antsim.c`: start direction N, right turn on white, step counting, onset definition and
the certification bbox snapshot (taken after step s, includes origin and initial black cells) all follow
CONVENTIONS.md; `first_initial_black_read` is correct because an initially-black cell can only be flipped by
being read. No defect found.
