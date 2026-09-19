# Code review of research/exhaustive/ (Langton's-ant exhaustive highway test)

Reviewer: independent code review + small targeted tests.  Nothing under
`research/exhaustive/` was modified; `exhaust.c` is compiled from a copy in `build/`.

Reproduce everything: `sh research/verify/exhaustive-review/run_all.sh`
(~2 minutes, at most 2 processes).  Outputs land in `out/`.

## Files
| file | what |
|---|---|
| `indep_sim.py` | independent dict-based simulator written from CONVENTIONS.md (not derived from exhaust.c / naive.py); also checks heading periodicity, per-period footprint and the true max abs coordinate along the trajectory |
| `test_records_vs_indep.py` | fresh build of exhaust.c on k=1,2,3 (all configs) and four k=5 ranges of 100 (incl. the claimed argmax 31064692 and argmin 17781263) with records=1; every CSV field (s, cert step, disp, dir, final pos, bbox, cells) compared with `indep_sim.py`; plus 202 rows of the finder's `out/k4_records.csv`.  Result: 1032 configs, 0 mismatches (`out/records_check.txt`) |
| `test_old_vs_new_binary.sh` | the k=5 run used an older binary; re-runs the two 131072-config probe ranges with the current source and compares `hist.bin` byte-for-byte and the summaries: IDENTICAL (`out/old_vs_new.txt`) |
| `test_stats_from_hist.py` | recomputes min/mean/median/max, tie counts, mode, log bins, direction counts, total steps from the raw `hist.bin`/summary files independently of analyze.py: all claims C7-C11 reproduced (`out/stats_check.txt`) |
| `test_boundary_cap.sh` | tiny-input edge cases: cap=100 step counting; cap=12335 exposes the status-3 misclassification; GRID=64 rebuild shows boundary detection fires at exactly the step the independent sim first reaches x<=-32, x>=31, y<=-32, y>=31 (512/512 consistent, no wrap) (`out/boundary_cap.txt`) |
| `out/maxabs_check.txt` | shows `max_abs_coord` is the max |final coordinate|, not the max ever reached (empty grid: 63 true vs 60 reported; k4 cfg 29641: 111 true vs 109 final) |

## Verdict summary
Simulation, onset definition, ring logic, certification and exhaustive coverage are correct.
Defects found (none changes a reported onset/certification number):
1. `exhaust.c:130` a run that hits the cap after 20 periods are verified but before the escape
   condition holds is labelled ST_NONTRAVEL ("periodic but not traveling") although it is
   traveling (demonstrated with cap=12335).  No run hit the cap, so counts are unaffected.
2. `exhaust.c:184-185` `max_abs_coord` uses only the final position; the true maximum
   |coordinate| along the trajectory is larger (by up to 7 in all sampled runs).  Claim C12's
   "largest |coordinate| the ant ever reached = 227" is really "largest |final coordinate|".
   The "far inside the grid" conclusion stands because boundary detection is exact.
3. Certification does not verify heading periodicity (dir(n)==dir(n-104)); the escape argument
   needs it.  Verified true in all 1032 sampled certifications; theoretical gap only.
4. "Per-period footprint 7x7" (naive.py, README) is window-phase dependent: measured 7x9 at the
   certification-step window.  Still < 20-cell margin, so the argument holds.
5. `exhaust.c:83-84` two `if`s on one line (gcc -Wmisleading-indentation); semantically correct.
6. The k=5 binary predates the current source; not verifiable from source, but the probe re-run
   (262,144 configs) reproduces the old binary's histograms byte-for-byte.
# note: out/*_hist.bin (20 MB each, derived) are deleted after the run; run_all.sh regenerates them
