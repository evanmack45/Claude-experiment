# random — the highway conjecture on random initial configurations

Everything follows `research/CONVENTIONS.md` (x East, y North, ant at (0,0) facing N,
white -> Right, black -> Left, t[k] = turn at step k, onset s = max{k : t[k] != t[k+104]},
certification = 20 exact periods + escape margin 20 beyond the pre-onset bounding box).
The certification rule is byte-for-byte the one in `research/exhaustive/exhaust.c`, so the
numbers are directly comparable with the exhaustive results.

## Reproduce every number with one command

    sh /home/user/Claude-experiment/research/random/run_all.sh

(~7 min wall time on 2 cores). It compiles `randexp.c`, runs the main sweep (two background
processes), runs `verify_py.py` (independent pure-Python cross-check), runs `run_extended.sh`
(three aggregate-only sweeps), then `analyze.py` writes

- `research/results/random_samples.csv`  one row per main-sweep sample
  (`k,p,seed,sample_index,outcome,onset_step,direction,steps_simulated`)
- `research/results/random_longest.json` the configuration with the longest certified onset
- `research/results/random.json`         per-(k,p) aggregates, totals, scaling fits, extended sweeps

Individual steps (exactly what `run_all.sh` runs):

    cd /home/user/Claude-experiment/research/random
    sh run_sim_only.sh          # compiles randexp.c; main sweep -> out/procA.csv, out/procB.csv (400000 rows)
    python3 verify_py.py        # -> out/verify_py.json  (must print "0 mismatches")
    sh run_extended.sh          # -> out/ext/, out/scale/, out/pfine/  (aggregate-only sweeps)
    python3 analyze.py          # -> ../results/random_samples.csv, random_longest.json, random.json
    python3 verify_longest.py   # optional: pure-Python re-simulation of the longest-onset configuration (~2 min)

## Sweeps
| sweep | k | p | samples/cell | seed | output |
|---|---|---|---|---|---|
| main | 5,8,12,16,24,32,48,64 | 0.1,0.25,0.5,0.75,0.9 | 10000 | 20260919 | per-sample CSV |
| ext | same | same | 100000 | 20260920 | onset list (uint32) + summary per cell |
| scale | 5..512 (14 values) | 0.5 | 10000 | 20260921 | same |
| pfine | 32 | 0.05..0.95 step 0.05 | 10000 | 20260922 | same |

Step cap 20,000,000; grid 4096x4096 with a boundary-hit outcome (never silently wrapped).

## Sampling scheme (deterministic per sample)
Cells of the box (`xmin = -(k//2)`, i.e. -floor(k/2) for odd k and -k/2 for even k) are visited in
order i = 0..k*k-1 with (x,y) = (xmin + i%k, xmin + i//k). splitmix64 is seeded with
`seed*0x9E3779B97F4A7C15 + sample_index*0xBF58476D1CE4E5B9 + k*0x94D049BB133111EB + round(1000p)*0xD6E8FEB86659FD93`
(mod 2^64); a cell is black iff `(r>>11)*2^-53 < p`. Any sample can be regenerated alone:

    ./randexp dump k p seed sample_index          # print its black cells
    ./randexp one  k p seed sample_index 20000000 # re-run it and print the full result

## Files
- `randexp.c`      simulator: modes `run` (per-sample CSV), `stats` (aggregate-only), `one`, `dump`
- `verify_py.py`   pure-Python re-implementation of RNG + ant + onset + certification; compares with the C rows
- `analyze.py`     aggregation, longest-onset extraction (with an independent re-run), numpy log-log fits, JSON export
- `run_sim_only.sh`, `run_extended.sh`, `run_all.sh`  drivers
- `out/`           raw outputs (procA/procB.csv have 18 columns: the 8 required ones followed by
                   n_black, dispx, dispy, final x, final y, bbox xmin, ymin, xmax, ymax of the pre-onset set, periods_verified)

## Definitional choices (stated explicitly)
- Onset s is the CONVENTIONS value (last mismatch index); the "first periodic step" reading would be s+1.
- The pre-onset bounding box includes the origin and the initial black cells as well as every cell modified in steps 1..s.
- Onset statistics are over certified samples (in every cell of every sweep, that was all samples).
- median = numpy.median (mean of the two middle values); percentiles = lower order statistic.
