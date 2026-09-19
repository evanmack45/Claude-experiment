#!/bin/sh
# One-command reproduction of every number in research/results/verify_literature.json.
# Runs offline on the files already in data/ (re-download commands are listed in README.md).
set -e
cd "$(dirname "$0")"
echo "== C3: independent ant simulation vs OEIS A261990 (300k steps)"
python3 ant_oeis_check.py data/b261990_verifier.txt 300000
echo "== b-file identity"
md5sum data/b261990_verifier.txt ../../literature/data/b261990.txt
echo "== PDF text extraction (own scraper) and phrase counts"
for f in math9501233 nlin0306022 1986-langton stewart_anty; do python3 pdftext.py data/$f.pdf > data/$f.txt; done
python3 phrase_counts.py
