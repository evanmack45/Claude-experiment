#!/bin/sh
# Reproduces every number in research/results/random.json from scratch.
# Usage: sh research/random/run_all.sh   (from any directory)
# ~7 min wall time on 2 cores (never more than 2 simulation processes at once).
set -e
cd "$(dirname "$0")"
sh run_sim_only.sh          # compiles randexp.c, main sweep -> out/procA.csv, out/procB.csv (400000 rows)
python3 verify_py.py        # independent pure-Python cross-check -> out/verify_py.json (must report 0 mismatches)
sh run_extended.sh          # aggregate-only sweeps -> out/ext/, out/scale/, out/pfine/
python3 analyze.py          # -> ../results/random_samples.csv, random_longest.json, random.json
