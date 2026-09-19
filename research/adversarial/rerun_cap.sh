#!/bin/sh
# Step-5 policy: re-run a configuration that did not certify at the 50M cap with a 10x cap and a 4x larger grid,
# logging position / bounding box / black-cell count every 10M steps so the trajectory can be described.
# usage: ./rerun_cap.sh <cfgfile>
cd "$(dirname "$0")" && ./antsim run "$1" --cap 500000000 --grid 32768 --log-every 10000000
