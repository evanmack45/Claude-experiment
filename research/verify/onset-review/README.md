# onset-review — code review + independent re-derivation of research/onset

Reviewer tests for the finder's Langton's Ant onset experiment (`research/onset/ant.c`, `analyze.py`,
`verify_py.py`). Nothing here modifies files outside this directory (work files go under `work/`).

## Reproduce everything with one command

    cd research/verify/onset-review && python3 review_tests.py 200000 && sh c_edge_tests.sh

- `review_tests.py` — a third, independent simulator (complex-number heading, set-of-black-cells grid,
  forward-scan onset finder). It re-derives every claimed number for all 200,000 steps and compares
  against `research/onset/out/*` and `research/results/onset*.json`: 56 checks, all pass
  (`review_tests_200000.log`). Includes: hand-worked first 5 steps; s=9977 with t[9977]='L', t[10081]='R';
  s-1 fails the definition; 0 mismatches after s; fundamental period of the suffix is 104 (not 52/26/...);
  state onset 9977; bbox (-19,29,-22,22) incl. origin; 1376 modified/visited; ant (-15,10) W; black 715/835/955;
  last pre-onset read 10183; margin>=1 at 11390; margin>=20 first 12336, permanent 12680 (12679 is <20);
  per-period min margin +2 exactly; turn string; 58R/46L; +12 black/period three ways; 40 offsets, 6x9 bbox,
  perp -7..3 (11 lines); trajectory JSON 12058 entries / 143205 bytes.
- `c_edge_tests.sh` — compiles ant.c with -Wall -Wextra (clean) and AddressSanitizer; N=200 and N=12000 are
  ASAN-clean; N=10 SEGVs at ant.c:102 (PX[N-104] with N<104: latent tiny-N bug, irrelevant to the claims);
  N=10 output matches the hand-worked trajectory; N=200000 rerun is bit-identical to research/onset/out/.

## Definitional alternatives computed here (informational)
- "first step strictly outside the pre-onset bbox": both coordinates beyond the bbox in the travel
  direction (finder's reading) = 11390; in ANY coordinate = 10095 (x < xmin); permanently outside in any
  coordinate = 10287.
- state-periodicity onset 9977 is defined as "smallest k with state periodic for all j >= k" (inclusive);
  under the turn-onset indexing (last non-matching index) it would read 9976.
