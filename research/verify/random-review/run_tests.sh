#!/bin/sh
set -e
D=/home/user/Claude-experiment/research/verify/random-review
cd "$D"
python3 test_reference.py
gcc -O2 -DGRID=128 -Wall -o test_boundary_reset test_boundary_reset.c -lm 2>/dev/null
./test_boundary_reset
sh test_csv_vs_one.sh
python3 test_seed_shift.py
python3 test_margin.py
echo ALL_REVIEW_TESTS_DONE
