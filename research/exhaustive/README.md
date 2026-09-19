# Exhaustive highway test over all initial configurations in small boxes

Every 2^(k*k) initial configuration in the k x k box of `research/CONVENTIONS.md`
(k = 1..5, ant at (0,0) facing North) was simulated until a 104-periodic highway
was *certified* or a cap of 5,000,000 steps was reached.  **k = 5 (33,554,432
configurations) was enumerated exhaustively, not sampled.**

## Reproduce everything with one command

    sh research/exhaustive/run_all.sh

(~4 s of CPU for k <= 4, ~17 min wall for k = 5 on two processes at ~105 Msteps/s each.)
It compiles `exhaust.c`, runs k = 1..5, runs the naive check, and runs `analyze.py`,
which writes `research/results/exhaustive.json` (the single source of every number below).

Individual pieces:

    gcc -O3 -march=native -o exhaust exhaust.c
    ./exhaust k lo hi cap outprefix [records] [strict]   # e.g. ./exhaust 4 0 65536 5000000 out/k4 1
    sh run_strict.sh                               # strict-certificate pass over k = 1..5 (see below)
    python3 naive.py 20000                         # independent empty-grid simulation
    python3 naive.py 130000 -2,-2 1,-2 0,-1 ...    # naive run on an explicit list of black cells
    python3 analyze.py                             # merge + statistics + cross-checks + JSON

## Files

| file | what |
|---|---|
| `exhaust.c` | C enumerator (grid 4096x4096, fast reset of touched cells only, per-config certification) |
| `naive.py` | deliberately simple, independent Python simulation used as a cross-check |
| `analyze.py` | merges `out/*`, computes stats/histograms, runs cross-checks, writes the results JSON |
| `run_all.sh` | one-command reproduction |
| `out/k{1..4}_records.csv` | one line per configuration (cfg index, status, s, certification step, displacement, direction, final position, bbox at onset, black cells) |
| `out/k{k}_hist_exact.csv` | exact histogram: (onset step s, number of configs), for every k; committed copies live in `research/results/histograms/` |
| `run_strict.sh`, `compare_strict.py`, `out/strict/` | strict-certificate pass and its comparison with the default pass (`research/results/exhaustive_strict.json`) |
| `out/k{k}_summary.txt`, `out/k5/half{0,1}_summary.txt` | raw per-run summaries printed by the C program |
| `out/*_hist.bin` | raw uint32 histograms (index = s, 0..cap); 20 MB each, derived, safe to delete |
| `out/*_special.txt` | runs that hit the cap / boundary / a non-traveling periodic regime (all empty) |
| `out/k5probe/` | 2 x 131,072-config throughput probe used to decide that full k=5 was feasible (superseded by the full run) |

## Strict certificate

The default stopping rule (20 exact periods of the turn sequence plus a 20-cell escape margin
of the *current* position) is the rule of `CONVENTIONS.md`. The adversarial review of the pull
request pointed out that it checks the margin at one position only and never checks the
heading, so on its own it is not a proof that the periodic regime continues for ever. Strict
mode (`./exhaust ... 1 1`, driven by `run_strict.sh`) replaces the stopping rule by a sufficient
certificate:

1. the turn sequence has repeated with period 104 for at least 20 full periods since the last
   mismatch at step L (as before);
2. the heading after step n equals the heading after step n-104, so the net rotation over a
   period is zero and, because the turns are periodic from L on, every period since L is a
   translate of the previous one by the same displacement (dx, dy), both components nonzero;
3. every one of the last 104 positions (not only the current one) is at least 20 cells beyond
   the bounding box of all cells modified in steps 1..L, the initial black cells and the origin,
   in both travel coordinates;
4. the bounding box of the last 104 positions is narrower, in each coordinate, than the
   displacement accumulated over the 20 verified periods (20 |dx| and 20 |dy|), so the cells read
   in any future period are disjoint from the cells read in the first period after L.

Why this suffices: the cells read in period j+1 are the cells read in period j translated by
(dx, dy). By (3) none of them was modified before step L (they lie outside the bounding box),
and by (2) and (4) the cell c read in period j+1 was touched in an earlier period j-m exactly when
the cell c-(dx,dy) read in period j was touched in period j-m-1, with no unmatched touches in
the first period after L. So c and c-(dx,dy) have the same state when read, the turns of period
j+1 repeat those of period j, and by induction the highway continues for ever; the margin only
grows. The strict rule never certifies earlier than the default rule (the empty grid certifies at
step 12,783 instead of 12,336) and the onset step s is unaffected, so the strict pass must
reproduce the default onset histograms exactly; `compare_strict.py` checks that and writes
`research/results/exhaustive_strict.json`.

Result of the strict pass (2026-09-19): all 2 + 16 + 512 + 65,536 + 33,554,432 configurations
certified strictly, 0 cap / boundary / non-traveling runs, every displacement exactly (+-2,+-2),
onset histograms bit-identical to the default pass for every k, latest strict certification step
236,323 (k = 5, 938 s on two cores).

Also fixed after the review: a run that reaches the cap while periodic but still waiting for
its escape margin is now reported as a cap hit (status 1), not as "periodic but not traveling"
(status 3, now reserved for a zero displacement component). No published run was affected
(no run ever reached the cap).

## Definitions used (exact readings of CONVENTIONS.md)

* Configuration index: bit i (0 <= i < k*k) is the colour of cell
  (xmin + i % k, ymin + i // k) with xmin = ymin = -(k // 2); set bit = black.
  For even k this is the box -k/2 <= x,y < k/2, for odd k it is -floor(k/2) <= x,y <= floor(k/2).
* Onset step s = max{ k >= 1 : t[k] != t[k+104] }, or 0 if there is no mismatch.
  The C code keeps a 128-entry ring of turns and compares t[n] with t[n-104] at every step.
* Certification (sound, exactly the convention): at step n we require
  1. n >= s + 2184, so that t[k] == t[k+104] has been verified for every k in s+1 .. n-104,
     i.e. for at least 2080 = 20 x 104 consecutive indices (20 full periods), and
  2. the ant's position after step n is at least 20 cells beyond the bounding box of all
     cells modified before step s+1 in *both* coordinates in its direction of travel.
     The bounding box is snapshotted at step s from a ring of per-step bounding boxes and
     includes the initial black cells and the origin (conservative reading of "modified
     before step s+1"; it can only make certification stricter, never change s).
     The direction of travel is the sign of pos(n) - pos(n-104); both components must be nonzero.
  The run stops at the first n satisfying both.  Runs that are 104-periodic but have a zero
  displacement component would be reported separately as "periodic but not traveling"
  (none occurred).  A run whose ant touches the outermost ring of the 4096x4096 grid is
  flagged as "boundary" (none occurred; the largest |coordinate| ever reached is reported).
* The measured spatial footprint of one highway period is 7 x 7 cells (naive.py, empty grid),
  so the margin of 20 is more than the strip half-width; combined with 20 verified periods this
  is the standard argument that the periodic regime continues forever.
* Median for an even count is the mean of the two middle order statistics (both are in the JSON).

## Results (all from research/results/exhaustive.json)

| k | configs | certified highway | hit cap | boundary | s min | s mean | s median | s max | max-s configuration (black cells) | directions +x,+y / +x,-y / -x,+y / -x,-y | max steps any run | total steps | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2 | 2 | 0 | 0 | 9977 | 9977.5 | 9977.5 | 9978 | [[0,0]] | 0 / 1 / 0 / 1 | 12337 | 24673 | 0 |
| 2 | 16 | 16 | 0 | 0 | 275 | 7234.1 | 9976.5 | 11386 | [[0,-1],[-1,0],[0,0]] | 4 / 5 / 3 / 4 | 14161 | 153512 | 0 |
| 3 | 512 | 512 | 0 | 0 | 200 | 4327.8 | 2374.5 | 43264 | [[-1,-1],[1,-1],[-1,0],[1,0],[-1,1],[1,1]] | 138 / 125 / 117 / 132 | 46248 | 3346179 | 0 |
| 4 | 65536 | 65536 | 0 | 0 | 155 | 3798.0 | 1736.5 | 119673 | [[-2,-2],[1,-2],[0,-1],[1,-1],[-2,0],[-1,0],[-2,1],[-1,1],[0,1]] | 16248 / 16430 / 16372 / 16486 | 122542 | 392952806 | 4 |
| 5 | 33554432 | 33554432 | 0 | 0 | 32 | 4250.4 | 2059.0 | 233232 | [[0,-2],[2,-2],[-2,-1],[-1,-1],[2,-1],[0,1],[2,1],[-2,2],[0,2],[1,2],[2,2]] | 8428157 / 8346625 / 8333103 / 8446547 | 235944 | 216439582470 | 1037 |

Log-spaced onset-step histograms (10 bins/decade) are in `results.k*.histogram_log_bins` of the JSON; exact histograms in `out/k*_hist_exact.csv`.

## Sanity check against the naive simulation

`python3 naive.py 20000` (empty grid) gives onset step s = 9977, certification at step 12336,
direction -x,-y, displacement (-2,-2) per period, bounding box at onset x in [-19,29], y in [-22,22].
`./exhaust 1 0 2 5000000 out/k1 1` gives the identical numbers for cfg 0 (see `out/k1_records.csv`).
`analyze.py` repeats this comparison for the empty grid, the single-black-cell grid and the
maximum-onset configuration of every k (all agree; see `sanity_checks_naive_python_vs_c` in the JSON).

## Notes / caveats

* The CSV record writer originally did not quote the direction field (which contains a comma);
  this was fixed and k = 1..4 were regenerated with the fixed binary.  The k = 5 run was started
  with the earlier binary, which differs only in that CSV line (records were disabled for k = 5)
  and in not printing the `n_disp_not_2_2` counter, so its summary lacks that key; the simulation
  and certification code is byte-for-byte the same.
* Nothing is sampled; no RNG is used anywhere.
