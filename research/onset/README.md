# onset — exact highway onset of Langton's Ant from the empty grid

Everything here follows `research/CONVENTIONS.md` (x East, y North, ant starts at
(0,0) facing N, white->Right, black->Left, step k = k-th rule application,
t[k] = turn at step k).

## Reproduce every number with one command

    cd research/onset && make all

This compiles `ant.c`, simulates 200,000 steps, cross-checks the first 15,000
steps against an independent pure-Python implementation (`verify_py.py`),
runs `analyze.py` (which recomputes the onset from the turn string, checks every
certification assertion, characterizes the highway, and writes
`research/results/onset.json` and `research/results/onset_trajectory.json`),
re-runs the simulator at N=100,000 and N=500,000 to show the onset is independent
of N, and renders two sanity PNGs (`out/grid_s.png`, `out/grid_s2080.png`).

Individual commands:

    gcc -O2 -Wall -o ant ant.c -lm
    ./ant 200000 out                      # raw data in out/ (turns.txt, traj.txt, onset.txt, black_*.txt)
    python3 verify_py.py out 15000        # independent Python cross-check
    python3 analyze.py out ../results     # all derived numbers + the two JSON files
    ./ant 100000 out100k; ./ant 500000 out500k   # N-independence of s

## Files
- `ant.c`         C simulator (byte grid sized from N, bounds guarded, records turns and (x,y,dir) per step)
- `verify_py.py`  pure-Python re-implementation; asserts identical turns/trajectory
- `analyze.py`    onset, certification, highway characterization, JSON export (all asserts must pass)
- `render_check.py` PNG sanity render
- `out/`          raw output of the 200k-step run (`onset.txt` is key=value summary)

## Headline results (from `research/results/onset.json`)
- onset step s = **9977** (t[9977]='L' != t[10081]='R'; t[k]==t[k+104] for all 9978 <= k <= N-104, N=200000 -> 1826 full periods, 0 mismatches; same s for N=100000 and 500000)
- period 104, displacement per period (-2,-2), direction "-x,-y" (south-west); 58 R and 46 L turns per period; 12 net black cells added per period; 40 distinct cells touched per period; strip spans 11 lattice diagonals (perp range -7..3), bbox of one period's offsets 6 x 9 cells
- ant at step s: (-15, 10) facing W. Cells modified at steps 1..s: 1376 cells, bbox x in [-19,29], y in [-22,22] (49 x 45); black cells at onset 715; max distance from origin before onset 34.67 (at step 8934), Chebyshev 29, Manhattan 48
- escape certification: margin >= 20 beyond the bbox in both coordinates first reached at step 12336 and permanently from step 12680; the per-period minimum margin grows by exactly 2 every period from step s on; the ant reads a pre-onset cell for the last time at step 10183.

## Definitional choices (stated explicitly)
- "modified before step s+1" = cells at positions after steps 0..s-1 (each step flips the cell under the ant).
- "cells visited before onset" = distinct positions after steps 0..s (here equal to the modified set: 1376).
- The alternative reading "periodic from step s onward" would report 9978 (= first step whose turn is periodic).
- State periodicity (position difference and direction 104-periodic) also starts at k = 9977.
