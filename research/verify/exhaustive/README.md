# Verification of research/exhaustive (skeptical re-derivation)

Everything here was written independently from `research/CONVENTIONS.md`; nothing was
copied from `research/exhaustive/`.

## One-command reproduction

    sh /home/user/Claude-experiment/research/verify/exhaustive/run_all.sh

(~4 s for k<=4, ~20-25 min wall for the full k=5 enumeration on two processes.)

## Pieces

| file | what |
|---|---|
| `vexh.c` | independent C enumerator: 2048x2048 grid, full per-step arrays (no rings), grid reset by replaying the position history, literal re-check of the onset step / periodicity / onset bounding box after every certified run, alternative certification step with the bounding box that excludes unvisited initial black cells, max coordinate over the whole path |
| `literal.py` | independent literal pure-Python simulation (dict grid, whole turn string, onset & certification by scanning) |
| `compare_small.py` | per-configuration comparison of my `out/k{1..4}.rec` with the finder's `out/k{1..4}_records.csv` |
| `compare_k5.py` | full comparison of my k=5 records with the finder's k=5 histograms, summaries and JSON (exact histogram equality, argmax/argmin, direction counts, total steps, log bins, mode, and the 200-config literal-Python sample) |
| `sample_k5_literal.py` | 200 random k=5 configs (python `random.Random(12345)`, `sample(range(2**25),200)`) through `literal.py` |
| `stats_from_finder_hist.py` | recomputes min/mean/median/max/mode/log-bins from the finder's raw `hist.bin` files with my own code |
| `footprint.py` | highway per-period footprint over all 104 window phases + strip width |
| `out/` | my outputs (`k*.rec` = 16-byte records per config: s, cert step, alt cert step, dx, dy, dir, status; `*.sum` summaries; logs) |

Record layout of `*.rec`: little-endian `uint32 s, uint32 cert, uint32 altcert, int8 dx, int8 dy, int8 dir (0:+x,+y 1:+x,-y 2:-x,+y 3:-x,-y), int8 status (0 cert, 1 cap, 2 boundary, 3 periodic-not-traveling)`.

## Individual commands

    gcc -O3 -march=native -Wno-misleading-indentation -o vexh vexh.c
    ./vexh 1 0 2 5000000 out/k1; ./vexh 2 0 16 5000000 out/k2; ./vexh 3 0 512 5000000 out/k3; ./vexh 4 0 65536 5000000 out/k4
    ./vexh 5 0 16777216 5000000 out/k5/h0 & ./vexh 5 16777216 33554432 5000000 out/k5/h1 & wait
    python3 compare_small.py; python3 sample_k5_literal.py; python3 compare_k5.py; python3 stats_from_finder_hist.py
    python3 literal.py 20000                      # empty grid
    python3 literal.py 237232 0,-2 2,-2 -2,-1 -1,-1 2,-1 0,1 2,1 -2,2 0,2 1,2 2,2   # k=5 max
    python3 footprint.py

Findings are summarised in `FINDINGS.md` (written after the k=5 run finished).
