#!/bin/sh
# The k=5 full run and the k5probe were produced by an OLDER binary (05:41) than
# the current exhaust.c (05:44).  Re-run the two probe ranges with a fresh build
# of the current source and compare hist.bin byte-for-byte and the summaries.
set -e
H=/home/user/Claude-experiment/research/verify/exhaustive-review
E=/home/user/Claude-experiment/research/exhaustive
$H/build/exhaust 5 0 131072 5000000 $H/out/probe_a 0 2>/dev/null
$H/build/exhaust 5 16777216 16908288 5000000 $H/out/probe_b 0 2>/dev/null
for p in a b; do
  if cmp $H/out/probe_${p}_hist.bin $E/out/k5probe/${p}_hist.bin; then echo "probe $p hist.bin IDENTICAL (old binary vs current source)"; else echo "probe $p hist.bin DIFFERS"; fi
  echo "-- summary diff (timing lines expected to differ; n_disp_not_2_2 line is new):"
  diff <(grep -v total_steps $E/out/k5probe/${p}_summary.txt) <(grep -v -e total_steps -e n_disp_not_2_2 $H/out/probe_${p}_summary.txt) && echo "probe $p summary IDENTICAL apart from timing"
  grep -o '"total_steps": [0-9]*' $E/out/k5probe/${p}_summary.txt $H/out/probe_${p}_summary.txt
done
