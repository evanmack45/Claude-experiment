# verify/random — skeptical re-derivation of research/random (random initial configurations)

Nothing here modifies the finder's files (exception: re-running their `verify_py.py` rewrote
`research/random/out/verify_py.json` with byte-identical content). All code below is my own,
written from `research/CONVENTIONS.md`.

## Reproduce everything (one command, ~10 min on 2 cores)

    cd /home/user/Claude-experiment/research/verify/random && sh run_main.sh && sh run_ext.sh && \
    gcc -O3 -march=native -o mysim2 mysim.c -lm && python3 compare_main.py && python3 compare_ext.py && \
    python3 check_aggregates.py && python3 check_rng.py && python3 soundness.py 200 12345 && \
    python3 soundness.py 1000 777 && python3 mypy_ant.py empty && python3 mypy_ant.py 64 0.75 20260919 4491 20000 && \
    python3 mypy_ant.py 64 0.9 20260920 96681 20000 && python3 mypy_ant.py 512 0.5 20260921 9269 20000

## What each piece does
- `mysim.c`  my C simulator: 8192x8192 grid, whole turn sequence and per-step bbox in flat arrays,
  onset recomputed post hoc from the full array (s = max{k: t[k]!=t[k+104]}), every k in s+1..n-104
  re-verified, true max |coordinate| over all steps tracked. Modes run/u32/one/dump/cells/long.
- `run_main.sh` re-runs the whole 400,000-config main sweep -> `out/myA.csv`, `out/myB.csv`;
  `compare_main.py` compares all 14 result fields row by row with the finder's procA/procB.csv.
- `run_ext.sh` re-runs the 4,330,000-config ext/scale/pfine sweeps -> `out/{ext,scale,pfine}/*.u32`;
  `compare_ext.py` compares the 73 onset lists byte for byte with the finder's and recomputes C7/C8/C12.
- `check_aggregates.py` recomputes C1,C4,C5,C6,C7,C10,C11,C12 from the finder's raw files with my own code
  (explicit sort medians, closed-form log-log slope).
- `check_rng.py` my pure-Python splitmix64 sampler vs `randexp dump` vs `mysim dump`; RNG-state
  collision check over all 4,730,000 (seed, idx, k, p) tuples; duplicate-config count in tiny boxes.
- `mypy_ant.py` my own pure-Python ant (dict grid) used on the empty grid and the three record configs.
- `soundness.py` extends a recorded-seed random subset of main-sweep runs to >=10x the certification
  step with no certification stop (`mysim2 long`) and checks s is unchanged and no mismatch follows.

## Results (all logs in out/)
- Main sweep: 400,000/400,000 rows agree on every field (out/compare_main.log). All certified.
- Ext/scale/pfine: 73/73 uint32 onset lists identical (out/compare_ext.log). 4,330,000 certified.
- Aggregates: every C4/C5/C6/C7/C10/C12 number reproduced exactly (out/check_aggregates.log).
- Pure Python: empty grid 9977/12336; k64 p0.75 idx4491 196974/199230 -x,-y; k64 p0.9 idx96681
  232914/238913; k512 idx9269 1323594/1337591 +x,-y (out/mypy_*.json).
- Soundness: 200 + 1000 random runs extended >=10x: 0 failures (out/soundness*.json). The longest main
  config extended to the 4094-cell boundary: 2021 periods, 0 mismatches.
- Discrepancy found: C11's "largest |coordinate| reached 224" is the largest |final coordinate|;
  the true maximum over all steps is 227 (k=64, p=0.75, sample 44). Far inside the grid either way.
