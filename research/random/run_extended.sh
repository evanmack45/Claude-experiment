#!/bin/sh
# Extended aggregate-only sweeps (part of run_all.sh):
#   ext:   the same 8x5 (k,p) grid, 100000 samples per cell, seed 20260920
#   scale: p=0.5, k from 5 to 512, 10000 samples each, seed 20260921
#   pfine: k=32, p from 0.05 to 0.95 step 0.05, 10000 samples each, seed 20260922
# Outputs go to out/ext/, out/scale/, out/pfine/ (uint32 onset lists + JSON summaries).
set -e
cd "$(dirname "$0")"
CAP=20000000
mkdir -p out/ext out/scale out/pfine
rm -f out/ext/*_summary.jsonl out/scale/*_summary.jsonl out/pfine/*_summary.jsonl
(for k in 5 12 24 48; do for p in 0.1 0.25 0.5 0.75 0.9; do ./randexp stats $k $p 20260920 100000 $CAP out/ext/k${k}_p${p}; done; done
 for k in 5 12 24 48 96 192 384; do ./randexp stats $k 0.5 20260921 10000 $CAP out/scale/k${k}; done
 for p in 0.05 0.15 0.25 0.35 0.45 0.55 0.65 0.75 0.85 0.95; do ./randexp stats 32 $p 20260922 10000 $CAP out/pfine/p${p}; done) 2> out/extA.log &
(for k in 8 16 32 64; do for p in 0.1 0.25 0.5 0.75 0.9; do ./randexp stats $k $p 20260920 100000 $CAP out/ext/k${k}_p${p}; done; done
 for k in 8 16 32 64 128 256 512; do ./randexp stats $k 0.5 20260921 10000 $CAP out/scale/k${k}; done
 for p in 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9; do ./randexp stats 32 $p 20260922 10000 $CAP out/pfine/p${p}; done) 2> out/extB.log &
wait
echo EXT_DONE
