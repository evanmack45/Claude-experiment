# research/literature — what is proven and what is open about Langton's Ant

Deliverable: `SOURCES.md` (claims with citations, verbatim quotes, and a
VERIFIED / SECONDARY / UNVERIFIED label on each), plus the machine-readable
summary `../results/literature.json`.

## Reproduce every computed number with one command

    cd research/literature && python3 check_oeis.py

This simulates Langton's ant exactly as defined in `../CONVENTIONS.md` (empty grid,
origin, facing North, white -> right, black -> left, flip, move) for 10,289 steps and
compares the colour read at each step with the OEIS A261990 b-file stored in
`data/b261990.txt` (downloaded 2026-09-19 from https://oeis.org/A261990/b261990.txt;
the script re-downloads it if the file is missing). It prints, and `data/check_oeis_output.json`
records:

* `mismatches_b(n)_vs_colour_read_at_step_n_plus_1 = 0`  (OEIS is 0-indexed: a(n) = colour read at step n+1)
* `oeis_index_from_which_b_is_104_periodic = 9977`
* `conventions_onset_step_s = 9977`, `first_periodic_step_1_based = 9978`

Exit status 0 means both checks passed. Pure Python, ~1 s, no dependencies.

## How the sources were read

* Web pages / arXiv HTML / Crossref JSON: fetched directly (URLs in SOURCES.md).
* PDFs (Gale et al. 1995 arXiv:math/9501233, Gajardo et al. arXiv:nlin/0306022,
  Langton 1986 scan from gwern.net): text extracted with `extract_pdf_text.py`
  (dependency-free FlateDecode + Tj/TJ scraper; spacing is lost, so quotes in SOURCES.md
  had their word spacing restored by hand without changing any word). Reproduce with
  `python3 extract_pdf_text.py <file.pdf>` after downloading the PDF.
* Paywalled primaries (Bunimovich–Troubetzkoy 1992, Gale 1993, Gale–Propp 1994,
  Stewart 1994, Troubetzkoy 1997) were NOT read; their content is labelled SECONDARY
  and rests on the refereed papers that cite them.

## Files

* `SOURCES.md` — the report.
* `check_oeis.py` — reconciliation of the literature's "9977" with CONVENTIONS.md.
* `extract_pdf_text.py` — PDF text scraper used for the primary sources.
* `data/b261990.txt` — OEIS A261990 b-file (input).
* `data/check_oeis_output.json` — output of `check_oeis.py`.
* `../results/literature.json` — results in the repo's JSON format.
