# verify/onset — independent re-derivation of research/results/onset.json

Skeptical re-check of the finder's claims in `research/onset/`. Nothing here modifies
the finder's files; their C and analyze.py were copied into `finder_build/` and run there.

## Reproduce everything (one command)

    cd research/verify/onset && python3 verify_onset.py 200000 && python3 verify_onset.py 500000 && gcc -O2 -o myant myant.c && ./myant 2000000

- `verify_onset.py N` : my own pure-Python simulator (dict grid, written from CONVENTIONS.md)
  plus recomputation of onset, certification, highway and pre-onset statistics.
  Outputs `my_<N>.log`, `my_<N>.json`, `my_turns_<N>.txt`.
- `myant.c` : my own C simulator; prints s, mismatches after s, periods (used for N=2,000,000).
- `finder_build/` : the finder's ant.c / analyze.py copied and run here; outputs diffed
  byte-for-byte against `research/onset/out/` and `research/results/onset*.json`.

## Result
Every claimed number reproduced exactly (s=9977; 0 mismatches over 1826 / 4710 / 19133
periods for N=200k / 500k / 2M; bbox [-19,29]x[-22,22], 1376 cells; ant (-15,10) W;
disp (-2,-2); margin-20 first 12336, permanent 12680, +2 per period; R=58 L=46; the
104-char turn string; 40 offsets, 6x9 bbox, 11 diagonals; 715/835/955 black cells;
max dist 34.669872 at step 8934 (unique), Chebyshev 29, Manhattan 48; trajectory JSON
12058 entries / 12057 turns / 715 & 955 cells / 143205 bytes).
`cmp my_turns_200000.txt ../../onset/out/turns.txt` is identical.
No literature claims were made by the finder, so none were fetched.
