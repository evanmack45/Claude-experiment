#!/bin/sh
# Compares rows written by the batch 'run' mode (procA/procB.csv, produced with 10000 samples in one process)
# against a fresh single-sample './randexp one' run for a few (k,p,idx), including the last sample of a cell.
# Any difference would indicate stale grid state between configurations.
R=/home/user/Claude-experiment/research/random
fail=0
for spec in "5 0.5 0" "5 0.5 9999" "64 0.9 9999" "64 0.75 4491" "32 0.1 5000" "8 0.9 7744"; do
  set -- $spec
  row=$(grep -m1 "^$1,$2,20260919,$3," $R/out/procA.csv $R/out/procB.csv | cut -d: -f2-)
  one=$($R/randexp one $1 $2 20260919 $3 20000000)
  s=$(echo "$one" | sed -E 's/.*"onset_step": ([0-9]+).*/\1/'); st=$(echo "$one" | sed -E 's/.*"steps_simulated": ([0-9]+).*/\1/'); d=$(echo "$one" | sed -E 's/.*"direction": "([^"]+)".*/\1/')
  exp="$1,$2,20260919,$3,certified,$s,\"$d\",$st"
  case "$row" in "$exp,"*) echo "OK   $row";; *) echo "DIFF csv=$row one=$exp"; fail=1;; esac
done
exit $fail
