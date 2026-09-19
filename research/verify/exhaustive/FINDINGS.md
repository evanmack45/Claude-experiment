# Findings (verifier of research/exhaustive)

Full independent re-enumeration of every configuration for k=1..5 with `vexh.c`
(2 x ~1100 s wall for k=5), plus literal pure-Python checks (`literal.py`).

* k=1..4: my per-config s, certification step, displacement and direction agree with the
  finder's `out/k{1..4}_records.csv` for all 2+16+512+65536 configs (`out/compare_small.log`).
* k=5: my exact histogram of s is IDENTICAL to the finder's `half0_hist.bin`, `half1_hist.bin`
  (per half and summed); status counts 33554432/0/0/0; argmax 31064692 (s=233232, cert 235418),
  argmin {17781263, 17781279} (s=32, cert 2216); direction counts 8428157/8346625/8333103/8446547
  (also per half); total steps 216,439,582,470 (106,095,159,010 + 110,344,423,460); max steps 235944;
  mode s=266 (88090); modal log bin [2512,3162) 2329415; top bin [199526,251189) 11; log bins identical
  to the finder's JSON (`out/compare_k5.log`).
* Literal re-check inside vexh.c (turn string scanned literally, onset bbox recomputed from positions)
  reported 0 failures and 0 bbox mismatches for all 33.6M + 65k configs; all displacements are (+-2,+-2)
  for k=5 too (the finder could only record the sign for k=5).
* Alternative bbox reading (exclude unvisited initial black cells): certification step never changes
  (n_altcert_differs = 0 for every k).
* 200 random k=5 configs (seed 12345) through literal.py agree with my C on s, cert step, displacement.
* Discrepancies found (C12 only): the finder's "largest |coordinate| ever reached" (227) is the max over
  FINAL positions; over the whole path it is 229 for k=5 (63/76/103/149 vs 60/73/99/146 for k=1..4).
  The "7x7 per-period footprint" holds for naive.py's window phase; over all 104 phases the extent
  ranges from (5,8) to (7,9) (`out/footprint.log`); strip width perpendicular to travel = 11 cells.
  Neither affects any conclusion (all far below the 20-cell margin / 2048 boundary).
* Stats arithmetic (mean/median/mode/log bins) recomputed from the finder's raw hist.bin with my own
  code: identical (`out/stats_from_finder_hist.log`).
* Finder's exhaust.c rebuilt from source reproduces `k4_records.csv` byte-for-byte and runs at
  105-107 Msteps/s on this machine (`out/finder_build/`), consistent with the claimed throughput.
