#!/bin/sh
# Verifier's full re-run of the finder's three aggregate-only sweeps with mysim (2 processes).
set -e
D="$(cd "$(dirname "$0")" && pwd)"
cd "$D"
mkdir -p out/ext out/scale out/pfine
rm -f out/ext/* out/scale/* out/pfine/*
(for k in 5 12 24 48; do for p in 0.1 0.25 0.5 0.75 0.9; do ./mysim u32 $k $p 20260920 100000 20000000 out/ext/k${k}_p${p}; done; done
 for k in 5 12 24 48 96 192 384; do ./mysim u32 $k 0.5 20260921 10000 20000000 out/scale/k${k}; done
 for p in 0.05 0.15 0.25 0.35 0.45 0.55 0.65 0.75 0.85 0.95; do ./mysim u32 32 $p 20260922 10000 20000000 out/pfine/p${p}; done; echo A_DONE) > out/extA.log 2>&1 &
(for k in 8 16 32 64; do for p in 0.1 0.25 0.5 0.75 0.9; do ./mysim u32 $k $p 20260920 100000 20000000 out/ext/k${k}_p${p}; done; done
 for k in 8 16 32 64 128 256 512; do ./mysim u32 $k 0.5 20260921 10000 20000000 out/scale/k${k}; done
 for p in 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9; do ./mysim u32 32 $p 20260922 10000 20000000 out/pfine/p${p}; done; echo B_DONE) > out/extB.log 2>&1 &
wait
echo EXT_DONE
