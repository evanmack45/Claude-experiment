# random-review — code review tests for research/random (randexp.c, analyze.py, verify_py.py)

Reviewer tests, all on tiny inputs (nothing here re-runs the sweeps). Run everything with

    cd /home/user/Claude-experiment/research/verify/random-review && sh run_tests.sh

| test | what it exercises | result |
|---|---|---|
| `test_reference.py` (+ `ref_ant.py`, the reviewer's own brute-force ant) | turn direction, initial heading, box coordinates, onset definition s = max{k: t[k]!=t[k+104]}, bbox of {origin, initial black, steps 1..s}, certification step, direction, final position, on 24 configs with k=1..5 | 24/24 identical to `./randexp one` |
| `test_boundary_reset.c` (compiles `randexp_lib.c`, a copy of randexp.c with GRID overridable and main renamed) | with GRID=128: a run that reaches the grid edge is reported `boundary` with the ant on the outer ring (no wrap); the cell array is all-zero after every run; the empty grid run after a boundary run gives 9977/12336; a config run twice with a big run in between gives identical results | 0 failures |
| `test_csv_vs_one.sh` | batch `run`-mode CSV rows (produced 10000 samples per process) vs a fresh `./randexp one` of the same sample, incl. the last sample of a cell | 6/6 identical |
| `test_seed_shift.py` | RNG defect: seed multiplier == splitmix64 gamma, so seed+1 = the same stream advanced by one output; demonstrates that sample idx of seed 20260920 is the raster-shift-by-one of sample idx of seed 20260919 (and seed 20260921 shift-by-two); then measures onset correlation main vs ext at the same idx | shift confirmed on 4 cells; onset correlation 0.003–0.02 (same as the idx+1 control), 0–5 identical onsets per 10000 |
| `test_margin.py` | soundness of the 20-cell escape margin: the highway's largest within-period backward excursion | dx=5, dy=7 < 20 |

Other checks done by reading (see the structured review output): step counting (n incremented before the step, t[n] stored at n&127, compared with n-104), ring buffer size 128 > 104 so entries are never overwritten before use, certification needs n >= s+2184 which verifies t[k]==t[k+104] for exactly >= 20 full periods, displacement measured over the last 104 steps with both components nonzero, boundary check before any array write, int64 step counters, uint32 onset storage (max 1.3e6), no modulo bias ((r>>11)*2^-53 < p).

Claim numbers were recomputed directly from research/random/out/procA.csv, procB.csv, out/ext, out/scale, out/pfine with the inline numpy snippet recorded in the review transcript (all matched random.json), and the three named samples (k=64 p=0.75 idx 4491; k=512 idx 9269; k=64 p=0.9 idx 96681) were re-run with `./randexp one`.
