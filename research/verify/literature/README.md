# research/verify/literature — skeptical verification of research/literature/

Verifier's own code and data only; the finder's files were not modified.

## Reproduce every number with one command

    sh research/verify/literature/reproduce.sh

It (1) runs my own simulator `ant_oeis_check.py` (written from CONVENTIONS.md, not copied) for
300,000 steps and compares with the OEIS A261990 b-file I downloaded myself
(`data/b261990_verifier.txt`, md5 800a0742a953a14f34c3ce8bcd7110fa, identical to the finder's copy);
(2) re-extracts text from the four PDFs in `data/` with my own scraper `pdftext.py`;
(3) prints phrase counts (`phrase_counts.py`) for every quote used in the verdicts.

Output of step (1): onset s = 9977, first periodic step 9978, t[9977]='L' != t[10081]='R',
t[9978]=t[10082]='L', drift per period (-2,-2), 2788 periods verified, bbox of cells modified in
steps 1..9977 = x in [-19,29], y in [-22,22], ant at step 9977 = (-15,10); 0 mismatches between
b(n) and the colour read at step n+1 (4842 mismatches at offset n, so OEIS is 0-indexed);
b-file 104-periodic from index 9977.

## Sources I fetched myself (all in data/)
Crossref JSON for every DOI in the claims (+ Grosfils 1999 via bibliographic query:
DOI 10.1023/a:1004611208149, J. Stat. Phys. 97:575-608, Nov 1999); arXiv PDFs math/9501233,
nlin/0306022, 2409.10124v1, 2505.05426, 2506.10482; gwern.net scan of Langton 1986; **Stewart 1994
(Sci. Am. July 1994) author's manuscript from the Wayback URL given in Wikipedia's citation**
(`data/stewart_anty.pdf`, 12 pages) — which the finder could not reach; MathWorld (2 pages),
Wikipedia wikitext, OEIS A261990/A282425, arXiv HTML of Etse 2606.26677v1, Lutfalla (x2),
Gajardo-Lutfalla-Rao, arXiv abstracts of Grosfils, Boon, Tokarz (ar5iv), Schuermann blog,
Stony Brook ants page, Troubetzkoy pub list.

Re-download commands: see the curl lines in `data/fetch_log.txt`.

## Main discrepancies found (details in the verdict JSON)
* C1/C2: finder's reproduce grep `which we will call a vant` matches nothing — the OCR layer reads
  "rant"/"oant" and "turns fight"; the SOURCES.md quote silently corrected OCR while claiming
  "wording untouched". Substance (title, journal, "vants") is correct: "Vants" occurs 3x in OCR.
* C6: finder's reproduce grep `theproofactuallyfirstappearedin[3]` fails (fi-ligature dropped ->
  "rst appeared"). Substance correct.
* C7: the proof paragraph is Stewart 1994 BOX 1 ("The Cohen-Kong Theorem: ant trajectories are
  unbounded") verbatim; Schuermann copied it. Schuermann lists "Ian Stewart. Travels with my ant."
  with no "lecture"/"Gresham" descriptor.
* C12: the figures 280,085,922 and 100,365,745 appear in NONE of the cited sources (GLR arXiv v1
  PDF + HTML, Lutfalla 2025a/b PDF + HTML) nor in web search. Sources actually give: LLRL ant
  reaches 384-period highway after 256,100 steps from the 0-uniform grid (GLR); Stewart 1994:
  "Ant 1101 ... highway-construction after 250,000 steps, cycle 388"; Tokarz: >1e13 (modified ants).
* C13: Stewart 1994 verified to use "Cohen-Kong Theorem" and "X.P.Kong and E.G.D.Cohen"
  (so Kong = X. P. Kong is stated, not inferred). "Originates with Stewart" is not established:
  Stewart cites Gale 1993, and Gale et al. 1995 say Gale 1993's attribution was already incorrect.
  Tokarz uses BOTH "Cohen-Kung" (2x) and "Cohen-Kong" (1x), not only "Cohen-Kung".
* Etse 2026 HTML (v1) does not cite arXiv math/0006108 (the "reference glitch" in SOURCES.md §9
  is not in the version I fetched); Etse gives Troubetzkoy 1997 as pp. 3-13 (finder: 3-15).
* Etse states explicitly that OEIS A282425 lists S_{n,n}-1 (finder only inferred this).
