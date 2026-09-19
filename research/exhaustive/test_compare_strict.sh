#!/bin/sh
# Negative test for compare_strict.py: a tampered reference histogram must make it exit non-zero
# (and an untampered one exit zero). Uses the k=1 strict output (2 configurations, < 1 s).
set -e
cd "$(dirname "$0")"
gcc -O3 -march=native -o exhaust exhaust.c
T=out/test_compare_strict; rm -rf "$T"; mkdir -p "$T/strict" "$T/ref_ok" "$T/ref_bad"
./exhaust 1 0 2 5000000 "$T/strict/k1" 1 1 2>/dev/null
printf 's,count\n9977,1\n9978,1\n' > "$T/ref_ok/k1_hist_exact.csv"
printf 's,count\n9987,1\n9988,1\n' > "$T/ref_bad/k1_hist_exact.csv"
python3 compare_strict.py --ks 1 --strict-dir "$T/strict" --ref-dir "$T/ref_ok" --result "$T/ok.json" > /dev/null \
  && echo "control (matching reference): exit 0 as expected" || { echo "FAIL: matching reference did not exit 0"; exit 1; }
if python3 compare_strict.py --ks 1 --strict-dir "$T/strict" --ref-dir "$T/ref_bad" --result "$T/bad.json" > /dev/null; then
  echo "FAIL: tampered reference exited 0"; exit 1
else
  echo "tampered reference: non-zero exit as expected"
fi
