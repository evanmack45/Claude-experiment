# Langton's Ant and the highway conjecture: what we established

Synthesis of five research agents (onset, exhaustive, random, adversarial, literature), each
independently checked by one or two skeptical verifiers who re-implemented the simulator from
`research/CONVENTIONS.md` and recomputed every number. Every value below is one a verifier
**confirmed**; where a verifier corrected a value the corrected value is used and the discrepancy
is noted; anything not independently checked is marked **UNVERIFIED**. Section 6 gives one
reproduction command per result. All conventions (coordinates, step counting, the onset step
`s`, certification) are those of `research/CONVENTIONS.md`.

---

## 1. The mystery

Langton's ant is a two-rule machine on an infinite grid of white cells: on a white cell it turns
right, flips the cell to black and moves one step; on a black cell it turns left, flips it to
white and moves. Started on an empty grid it draws a symmetric doodle, then wanders in what
looks like random scribbling for about ten thousand steps, and then, abruptly, starts laying a
"highway": a 104-step cycle that repeats for ever and carries the ant off diagonally, two cells
per cycle. Every finite starting pattern anyone has ever tried ends the same way, in a highway.
The **highway conjecture** says this always happens: for every initial configuration with
finitely many black cells, the ant eventually builds the highway. Forty years after Langton's
1986 paper, nobody has proved it or found a counterexample. The rule is fully deterministic and
reversible, so in principle everything about it is computable; in practice the only theorem we
have is that the ant never stays in a bounded region. This report records what we could
establish by brute-force computation and what the literature has actually proved.

## 2. What is proven (literature)

Citations are to `research/literature/SOURCES.md` (S-numbers) as checked by the literature
verifier (`research/verify/literature/`). "VERIFIED" means the primary text was read by both
the finder and the verifier; "SECONDARY" means only refereed papers citing it could be read.

* **Origin.** Christopher G. Langton, "Studying artificial life with cellular automata",
  *Physica D* 22(1-3):120-149, October 1986, doi:10.1016/0167-2789(86)90237-X (S1, VERIFIED via
  Crossref and the OCR scan). He calls them "vants". His paper contains no "10,000", no "104"
  and no word "highway"; it mentions only "a periodic, self-limited pathway" (Plate 8). The
  OCR layer of the scan reads "which we will call a rant" ("vant" with an OCR error), so the
  quote in SOURCES.md was silently OCR-corrected; the word "Vants" does appear verbatim.
* **Unboundedness theorem.** For every initial configuration the ant's trajectory is unbounded.
  First proved by L. A. Bunimovich and S. E. Troubetzkoy, "Recurrence properties of Lorentz
  lattice gas cellular automata", *J. Stat. Phys.* 67(1-2):289-302, 1992, doi:10.1007/BF01049035
  (S2; bibliographic data VERIFIED, paper content SECONDARY because it is paywalled). The
  attribution is stated explicitly by Gale, Propp, Sutherland and Troubetzkoy 1995 (S5,
  VERIFIED): "Fundamental Theorem of Myrmecology (Bunimovich-Troubetzkoy): An ant's track is
  always unbounded. ... the attribution given there is incorrect; the proof actually first
  appeared in [3]." The popular name "Cohen-Kong theorem" is a misattribution: Ian Stewart,
  *Scientific American* 271(1):104-107, July 1994 (S6, now VERIFIED by the verifier from the
  Wayback copy) writes "X.P.Kong and E.G.D.Cohen proved that the ant's trajectory is
  necessarily unbounded" and titles its Box 1 "The Cohen-Kong Theorem"; Stewart himself cites
  Gale 1993, which Gale et al. 1995 say already carried the wrong attribution, so the name's
  first use is not established. MathWorld spells it "Cohen-Kung"; Tokarz 2018 uses both spellings.
* **Proof idea (corner-cell argument).** Reversibility makes any bounded orbit periodic; take
  the visited cell furthest up-and-right; each visit flips it, so on alternate visits the ant
  must exit into a never-visited cell. Contradiction. The paragraph quoted in SOURCES.md is
  verbatim Box 1 of Stewart 1994 (VERIFIED), reproduced by Martin and Schuermann 2017 (S13).
* **No-corner theorem** (Troubetzkoy, Lewis-Parker lecture, *Alabama J. Math.* 21(2), 1997; S7,
  SECONDARY via Gajardo et al. 2002 and Etse 2026): the set of cells exited infinitely often has
  no corner.
* **Computational complexity.** Gajardo, Moreira, Goles, "Complexity of Langton's ant",
  *Discrete Applied Mathematics* 117(1-3):41-50, 2002, doi:10.1016/S0166-218X(00)00334-6 (S8,
  VERIFIED): a single ant on a finite configuration can evaluate any boolean circuit, so
  cell-reachability is **P-hard** (not shown P-complete); universality and undecidability hold
  only for infinite (finitely described) configurations. Decidability for finite support is
  open. The same paper states the highway conjecture verbatim: "For any initial configuration
  with finite support, the ant eventually starts building the periodic highway, in some
  unobstructed direction."
* **Highway geometry in the literature.** Period 104 and drift (+-2,+-2) per period (MathWorld
  S20; Lutfalla 2025 S17; Boon 2001 S10 gives the exact speed sqrt(2)/52 = |(2,2)|/104). The exact
  empty-grid onset 9977 appears in OEIS A261990 (S11) and Tokarz 2018 (S14); "about 10,000" in
  Gale et al. 1995 and Gajardo et al. 2002 is a rounding; MathWorld's 10,647 is a figure-caption
  step count, not an onset.
* **Generalized ants.** Gale et al. 1995 (S5, VERIFIED) define rule-string ants and prove
  recurrent bilateral symmetry for strings with the even run-length property (e.g. LRRL, LLRR)
  via Truchet tiles; those ants provably return to the origin for ever and never build a highway,
  so the conjecture is specific to the LR ant. Gajardo-Lutfalla-Rao 2025 (S15) and Lutfalla
  2025 (S16, S17) show cousins (LLLR, LLRRRL, LLRLRLL) with several highways or non-highway
  behaviour. The longest other-rule transients the sources actually document are 256,100 steps
  (LLLR from the empty grid, S15) and Stewart's "Ant 1101" at about 250,000 steps; Tokarz 2018
  reports modified ants exceeding 10^13 steps (abstract only).
* **Triangular lattice.** Grosfils, Boon, Cohen, Bunimovich, *J. Stat. Phys.* 97:575-608, 1999
  (S9, SECONDARY: arXiv abstract only): propagation is a theorem on the triangular lattice,
  "regardless of the precise state of the medium".
* **Escape bounds.** Etse, arXiv:2606.26677 (June 2026; S18, VERIFIED): an n x n domain is
  escaped within (n+1)! steps; exact confinement maxima S(n,n) = 1, 6, 17, 46, 85, 164, 262, 488,
  679 for n = 1..9 (OEIS A282425 lists S(n,n)-1; Etse states this explicitly).
* **Status.** OPEN as of June 2026: Lutfalla 2025 "little progress has been made towards
  proving or disproving this conjecture"; Gajardo-Lutfalla-Rao 2025 "no simulation suggest the
  conjecture might be false"; Etse 2026 "has never been formally established".
* **No published record** of a longest transient for Langton's LR ant from a finite non-empty
  configuration was found ("none found", not "none exists"). Two figures in an early draft of
  SOURCES.md (280,085,922 and 100,365,745 steps for other rules) occur in none of the cited
  papers and are **dropped**.

## 3. What we computed

All simulators are C (100-108 million steps/s) cross-checked by independent pure-Python
implementations; every verifier wrote its own simulator from CONVENTIONS.md and reproduced the
finders' outputs byte-for-byte or row-for-row.

### 3.1 Onset from the empty grid (`research/onset/`, `research/results/onset.json`)

Confirmed by two verifiers (`research/verify/onset/`, `research/verify/onset-review/`), who
reproduced the 200,000-step turn string byte-for-byte.

| quantity | value |
|---|---|
| onset step s (CONVENTIONS: t[k]==t[k+104] for all k >= s+1) | **9977** (t[9977]='L', t[10081]='R') |
| alternative reading "periodic from step s inclusive" | 9978 |
| state periodicity (position differences and direction) begins at | 9977 (inclusive index) |
| period / displacement per period / direction | 104 / (-2,-2) / -x,-y (south-west) |
| ant after step s | (-15, 10) facing West |
| turns per period | 58 R, 46 L, net +12 black cells per period |
| distinct cells touched per period | 40, in a 6 x 9 box, on 11 consecutive lattice diagonals |
| 104-char turn string from step 9978 | LRLLRRRRLLRLLRRRRLLRRRRLLRLRRRRLRLLLLRRRRLRRLRRRRLLLLRLRRRRLRRRRLLLLRLRRRRLRLLRRLLLLRRLLRRRRLLRRLRLLRLLR |
| cells modified before onset | 1376, bbox x in [-19,29], y in [-22,22] (49 x 45) |
| black cells at onset | 715 (52% of the touched cells) |
| farthest pre-onset excursion | 34.67 cells from the origin (r^2 = 1202) at step 8934; Chebyshev 29, Manhattan 48 |
| last step reading a chaos-era cell | 10183 |
| first step strictly outside the pre-onset bbox (both travel coordinates) | 11390 (any coordinate: 10095) |
| escape margin >= 20 cells first reached / permanent | 12336 / 12680 |
| periods verified mismatch-free | 1826 (N=200,000), 4710 (N=500,000), 19133 (verifier, N=2,000,000) |

Certification: from step 12680 on the ant is >= 20 cells beyond the pre-onset bounding box in
both travel coordinates, the per-period minimum margin grows by exactly 2 every period, and the
per-period offset set is identical for every period start. Permanence beyond the simulated
range is therefore an inference from the verified strip geometry, as CONVENTIONS.md intends,
not a computed fact.

### 3.2 Exhaustive small boxes (`research/exhaustive/`, `research/results/exhaustive.json`)

Every one of the 2^(k*k) configurations in the k x k box for k = 1..5 was simulated (k = 5
enumerated in full, 33,554,432 configurations, 216,439,582,470 ant steps, 1037 s wall on two
processes). Verifier 1 re-enumerated all of them with a differently designed C program and got a
bit-identical onset histogram; verifier 2 recomputed all statistics from the raw histograms.

| k | configs | certified | cap/boundary | min s | mean s | median s | max s | max-onset configuration |
|---|---|---|---|---|---|---|---|---|
| 1 | 2 | 2 | 0 | 9977 | 9977.5 | 9977.5 | 9978 | black origin cell |
| 2 | 16 | 16 | 0 | 275 | 7234.06 | 9976.5 | 11386 | [(0,-1),(-1,0),(0,0)] |
| 3 | 512 | 512 | 0 | 200 | 4327.80 | 2374.5 | 43264 | [(-1,-1),(1,-1),(-1,0),(1,0),(-1,1),(1,1)] |
| 4 | 65,536 | 65,536 | 0 | 155 | 3797.99 | 1736.5 | 119673 | [(-2,-2),(1,-2),(0,-1),(1,-1),(-2,0),(-1,0),(-2,1),(-1,1),(0,1)] |
| 5 | 33,554,432 | 33,554,432 | 0 | 32 | 4250.45 | 2059.0 | 233232 | [(0,-2),(2,-2),(-2,-1),(-1,-1),(2,-1),(0,1),(2,1),(-2,2),(0,2),(1,2),(2,2)] |

* Every certified run has displacement exactly (+-2,+-2) per 104 steps (the finder recorded
  only the sign for k = 5; verifier 1's re-enumeration checked the full displacement).
* k = 5 shortest onset: s = 32, attained by exactly two configurations (indices 17781263 and
  17781279; the first has 12 black cells, direction -x,+y, certified at step 2216).
* k = 5 most common exact onset: s = 266 (88,090 configurations); modal log-bin [2512, 3162)
  with 2,329,415.
* Highway directions at k = 5: +x,+y 8,428,157; +x,-y 8,346,625; -x,+y 8,333,103; -x,-y
  8,446,547 (within 0.7% of uniform).
* Longest single run 235,944 steps. Largest |coordinate| on any path: **229** (the finder
  reported 227, which is the max |final coordinate|; both verifiers found the counter measured
  only the final position; the 4096-grid boundary at 2048 was never approached).
* Median onset falls with box size (9977 -> 2374 -> 1736 -> 2059) while the maximum grows
  roughly 2x per k (43264 -> 119673 -> 233232).

### 3.3 Random sweep (`research/random/`, `research/results/random.json`)

Main sweep: k in {5,8,12,16,24,32,48,64} x p in {0.1,0.25,0.5,0.75,0.9} x 10,000 samples =
400,000 configurations (seed 20260919, cap 2e7 steps), every row in
`research/results/random_samples.csv`. Verifier 1 re-ran all 400,000 with its own simulator (0
disagreements in 14 fields) and all 4,330,000 extended-sweep configurations (73 onset lists
byte-identical).

* 400,000 / 400,000 certified; 0 cap, 0 boundary. Onset min 101, median 5767, mean 9788.37,
  max 196,974; **67.4%** of the 400,000 main-sweep configurations reach the highway sooner than the
  empty grid (pooled over all 4,730,000 draws, from the per-cell counters: 3,139,738 / 4,730,000 = 66.4%).
* Directions: +x,+y 100,245; +x,-y 98,961; -x,+y 100,527; -x,-y 100,267.
* Longest main-sweep onset: 196,974 (k=64, p=0.75, sample 4491, 3121 black cells, -x,-y,
  certified at 199,230); cell list in `research/results/random_longest.json`.
* Longest single run 199,230 steps; largest |coordinate| at any step **227** (the finder's
  224 is the max |final coordinate|).
* All sweeps together: **4,730,000 random draws, 4,730,000 certified highways**, boxes up to
  512 x 512 with up to ~131,000 black cells. These are runs, not distinct patterns: a Bernoulli(p)
  draw in a small box often repeats an earlier draw (the 560,000 draws in the 5 x 5 box contain
  only 327,611 distinct patterns, the 560,000 draws in the 8 x 8 box 553,399; in 12 x 12 and
  larger boxes repeats are negligible), so the number of distinct random configurations is at
  most about 4,491,000 (`research/random/count_distinct.py`). An earlier version of this
  section called all 4,730,000 draws distinct; that was wrong (found by the adversarial review on
  the pull request). Second caveat, found by verifier 2: the seed
  multiplier in `randexp.c` equals the splitmix64 increment, so the "extra seeds" 20260920-22
  are the main stream shifted by 1-3 outputs; overlapping (k,p) cells contain raster-shifted
  copies of main-sweep configurations. They are distinct, valid Bernoulli(p) boxes and their
  onsets are uncorrelated with the originals (pair correlation 0.003-0.02, same as control), so
  the counts stand, but the sweeps are not independent replicates.
* Scaling at p = 0.5: median onset 2084.5 (k=5), 2676, 3458.5, 4267.5, 5980.5, 7801.5, 11037,
  15472 (k=64); log-log slope 0.788 over all k, 0.953 for k >= 24. Scaling sweep (seed
  20260921, 10,000 samples per k, all certified): medians 14966.5 (k=64), 22185, 31523, 48029.5,
  68823.5, 108796.5, 159241 (k=512); median ~ k^1.138 over k = 64..512 (r^2 0.9986), i.e.
  ~ N^0.569 in the number of black cells. Within this range the median grows far more slowly than
  the diffusive k^2 one might guess, but this is a finite-range fit of the onset step at one
  density (seven box sizes), not a measurement of transport and not an asymptotic law; the
  main-sweep slope also depends on the fitted range (0.788 over k = 5..64, 0.953 for k >= 24).
  The stale "k^2 (diffusive exit)" note in random.json has been corrected.
* Density sweep at k = 32 (190,000 configs, all certified): median 6942 (p=0.05) to 10147
  (p=0.95); mild dependence.
* **Longest onset found anywhere in the project: 1,323,594 steps**, k=512, p=0.5, seed 20260921,
  sample 9269, 130,511 black cells, direction +x,-y, certified at step 1,337,591 (reproduced by
  both the finder's tool and the verifier's C and Python). Extended 40-cell sweep record:
  232,914 (k=64, p=0.9, seed 20260920, sample 96681).

### 3.4 Adversarial attacks (`research/adversarial/`, `research/results/adversarial.json`)

Verifier (`research/verify/adversarial/`) re-simulated every A, C and D run and 60,000 GA rows
with its own simulator, re-implemented the D chain from scratch, and found 0 mismatches.

* Totals: **3,484,889 simulation runs, 0 non-certified, cap (5e7) never hit**. The finder
  called these "configurations"; the verifier found 806,799 duplicate GA genomes, so the number
  of distinct configurations is about 2,677,946 (2,676,229 distinct GA genomes).
  Evidence and reproduction: `sh research/adversarial/run_all.sh` regenerates attacks A, C, D and
  the two main GA runs deterministically (21,861 runs). The two extended GA runs (1,742,445 and
  1,720,583 evaluations) were wall-clock-limited and are archived, not regenerated: their
  complete evaluation logs are committed as `research/adversarial/evidence/*.csv.gz`, and
  `python3 research/adversarial/count_evidence.py` recounts them (3,483,028 GA evaluations in all,
  0 non-certified, 2,676,229 distinct genomes, best 233,232) and re-simulates a random sample of
  rows with `antsim`. Before this evidence was committed the 3,484,889 total could not be
  audited from the repository (found by the adversarial review on the pull request).
* Attack A (obstacles on the empty-grid highway): 1512 placements, 616 actually hit, 896 missed
  (every miss gives exactly 9977). All 616 hits re-formed a certified highway with a
  re-randomised direction (+x,-y 238; -x,-y 264; -x,+y 85; +x,+y 29). Extra chaos after contact:
  min 564, median 5012, mean 10883, p90 26156, max 138,873; 63.6% of hits re-form faster than
  the empty grid. Longest A onset 190,600 (L-shaped obstacle 377 periods ahead, contact at
  51,727).
* Attack B ((1+lambda) hill-climb in the 12 x 12 box, 3,483,028 evaluations): best 233,232,
  which is the k = 5 exhaustive maximum used as a start point and never improved; best from
  purely random starts 206,374. Single-cell flips reshuffle the onset almost completely, so the
  climb barely beats random sampling. Main 2 x 10,000-evaluation runs are byte-for-byte
  deterministic; the extended runs were stopped early at ~270 s by the harness (recorded, the
  SIGTERM itself is UNVERIFIED).
* Attack C (structured seeds): 202 distinct configurations (203 named; hollow_square_3 equals
  ring8), all certified; longest non-reference: concentric_rings_13 at 43,621.
* Attack D (greedy chaining of 2 x 2 obstacles on successive highways inside |x|,|y| <= 300):
  four obstacles, 16 black cells, onset **259,274** = 25.99 x the empty grid, direction -x,-y,
  certified at 276,869; stage onsets 51,033 / 145,886 / 187,236 / 259,274.

### 3.5 The longest onset found anywhere, and its configuration

* Absolute record: **1,323,594 steps** (random sweep, k = 512, p = 0.5, seed 20260921,
  sample_index 9269, 130,511 black cells, highway +x,-y, certified at 1,337,591; regenerate with
  `./randexp one 512 0.5 20260921 9269 20000000` or `./randexp dump 512 0.5 20260921 9269`).
* Longest onset from a hand-constructed pattern: **259,274 steps from 16 black cells** (Attack D,
  cells listed in `research/adversarial/out/attack_d_final.cfg` and adversarial.json). Per black
  cell the 11-cell 5 x 5 maximum is the larger record (233,232 / 11 = 21,203 steps per cell versus
  259,274 / 16 = 16,205).
* Provable record within a 5 x 5 box: **233,232 steps from 11 black cells** (exhaustive; this
  is the true maximum over all 33,554,432 patterns in that box).

## 4. What this evidence does and does not say

It says: in roughly 41.8 million simulated runs (33.6 M exhaustive + 4.73 M random + ~3.48 M
adversarial), covering every pattern in a 5 x 5 box, random boxes up to 512 x 512, structured
seeds, obstacles dropped on running highways, and millions of hill-climb mutations, **not one
run failed to reach a certified 104-step highway**, and the longest run used 6.7% of its step cap
(1,337,591 of 20,000,000 steps; every other run used less). The typical onset in a random box grows only about linearly with the box side,
and most perturbations of the empty grid shorten the chaotic phase. The onset landscape is
rough (single-cell flips reshuffle it) and heavy-tailed (the 5 x 5 maximum is 7300x its minimum).

It does not say the conjecture is true. Finite enumeration cannot prove a statement about
infinitely many configurations, and the literature is explicit that this is exactly the
situation: "no simulation suggest the conjecture might be false" (Gajardo-Lutfalla-Rao 2025) is
evidence, not proof. Three honest limits: (i) our largest exhaustive box is 5 x 5; a
counterexample could need a specific large pattern that random sampling never hits; (ii) our
certification proves a highway is permanent only relative to the finite modified set, which is
sound, but "onset within the cap" is a property of the runs we did; (iii) even the proven
unboundedness theorem does not rule out an ant that wanders for ever without becoming periodic.
What the computations do establish rigorously is a list of exact finite facts (the 5 x 5
maximum 233,232 is a theorem about that box), plus a well-measured statistical picture.

## 5. Ten movie-worthy facts

| # | fact | exact value | supporting file |
|---|---|---|---|
| 1 | From an empty grid the ant scribbles for 9,977 steps, then repeats a 104-step cycle for ever | s = 9977; period 104 | research/results/onset.json |
| 2 | The chaos blob: cells touched, black cells, size, farthest excursion | 1376 cells, 715 black, 49 x 45 box, 34.67 cells at step 8934 | research/results/onset.json |
| 3 | One highway cycle: turns, cells touched, net trail | 58 R / 46 L, 40 cells touched, +12 black cells, moves (-2,-2) | research/results/onset.json |
| 4 | The ant keeps grazing chaos-era cells after onset, and is only provably clear at | last chaos-cell read 10183; margin 20 permanent from 12680 | research/results/onset.json |
| 5 | Every one of the 33,554,432 patterns in a 5 x 5 box builds a highway | 33,554,432 / 33,554,432; 216,439,582,470 steps; 1037 s | research/results/exhaustive.json |
| 6 | The fastest highway ever: a 5 x 5 pattern that is on the road after 32 steps | s = 32, 12 black cells, cfg 17781263 | research/results/exhaustive.json |
| 7 | The slowest 5 x 5 pattern: 11 black cells, 23x longer than the empty grid | s = 233,232, certified at 235,418 | research/results/exhaustive.json |
| 8 | 4,730,000 random draws, all highways; most perturbations shorten the chaos | 4,730,000 / 4,730,000 (at most ~4.49 M distinct); 67.4% of the main sweep faster than 9977 | research/results/random.json |
| 9 | The longest onset found anywhere: a 512 x 512 box with 130,511 black cells | 1,323,594 steps | research/results/random.json |
| 10 | Drop a block on the highway: the ant always rebuilds one; chain four blocks and it takes 259,274 steps | 616/616 rebuilt, median 5012 extra steps; 16 cells -> 259,274 | research/results/adversarial.json |

Bonus (verified): median onset in a p = 0.5 box grows like k^1.14 for k = 64..512
(`research/results/random.json`, results.scaling_sweep_p05).

## 6. Reproduction (one command per result)

All paths are relative to the `research/` directory of the repository. The finder commands are the
primary route; the verifier commands re-derive the same numbers with independent code. Commands
marked (long) take minutes to tens of minutes.

| result | command |
|---|---|
| onset s = 9977 and all of 3.1 (finder) | `cd onset && make all && grep '^s=' out/onset.txt` (rewrites out/ and results/onset*.json deterministically) |
| same, independent (verifier) | `cd verify/onset && python3 verify_onset.py 200000` |
| 104-char turn string | `cut -c9978-10081 onset/out/turns.txt` |
| escape margins 12336 / 12680, alt onsets 9978 / 10183 / 11390 | `python3 -c "import json;r=json.load(open('results/onset.json'))['results'];print(r['certification'],r['alternative_onset_numbers'])"` |
| exhaustive k = 1..5 (long, ~17 min for k=5 on 2 cores) | `sh exhaustive/run_all.sh` |
| exhaustive stats from stored histograms (fast) | `python3 exhaustive/analyze.py` |
| exhaustive independent re-enumeration (long) | `cd verify/exhaustive && sh run_all.sh` |
| max any-step coordinate 229 | `grep max_abs verify/exhaustive/out/k5/h0.sum verify/exhaustive/out/k5/h1.sum` |
| k = 5 maximum 233232 in pure Python | `cd exhaustive && python3 naive.py 237232 0,-2 2,-2 -2,-1 -1,-1 2,-1 0,1 2,1 -2,2 0,2 1,2 2,2` |
| k = 5 minimum 32 in pure Python | `cd exhaustive && python3 naive.py 5000 -2,-2 -1,-2 0,-2 1,-2 2,-1 0,0 2,0 -1,1 0,1 1,1 2,1 2,2` |
| random main sweep (long) and aggregates | `sh random/run_all.sh` ; aggregates only: `python3 random/analyze.py` |
| random extended sweeps (long) | `cd random && sh run_extended.sh && python3 analyze.py` |
| random independent re-run (long) | `cd verify/random && sh run_main.sh && python3 compare_main.py` |
| main-sweep record 196974 | `cd random && ./randexp one 64 0.75 20260919 4491 20000000 && python3 verify_longest.py` |
| absolute record 1323594 | `cd random && ./randexp one 512 0.5 20260921 9269 20000000` |
| seed-shift caveat | `cd verify/random-review && python3 test_seed_shift.py` |
| adversarial A, C, D, B main (~30 s) | `cd adversarial && sh run_all.sh` |
| archived extended GA evidence recount + 200-row re-simulation | `cd adversarial && python3 count_evidence.py` |
| random draws: distinct-pattern counts (5 x 5, 8 x 8) | `cd random && python3 count_distinct.py` |
| Attack D record 259274 | `cd adversarial && ./antsim run out/attack_d_final.cfg` |
| Attack B best 233232 | `cd adversarial && ./antsim run out/attack_b_best.cfg && python3 verify_py.py out/attack_b_best.cfg 237392` |
| adversarial independent re-simulation | `cd verify/adversarial && ./run_all.sh` |
| distinct-configuration count | `cd verify/adversarial && python3 check_distinct.py` |
| OEIS A261990 agreement | `cd literature && python3 check_oeis.py` |
| literature greps (unsourced numbers absent, Stewart's "Cohen-Kong") | `cd verify/literature && python3 phrase_counts.py` |

What the synthesizer re-ran on 2026-09-19 to settle finder/verifier disagreements:
`grep max_abs verify/exhaustive/out/k5/*.sum verify/exhaustive/out/k?.sum` and
`grep max_abs_coord exhaustive/out/k*_summary.txt exhaustive/out/k5/*_summary.txt` (229 vs 227);
`grep -E 'TRUE max|max \|final' verify/random/out/compare_main.log` (227 vs 224);
`cd verify/random-review && python3 test_seed_shift.py` (defect confirmed);
`cd verify/adversarial && python3 check_distinct.py && python3 check_c.py` (2,677,946 distinct; 202 seeds);
the literature greps for 280,085,922 / 100,365,745 (0 hits in all six cached sources) and for
"Cohen-Kong Theorem" in Stewart 1994 (present);
`cd verify/onset && python3 verify_onset.py 200000`;
`cd random && ./randexp one 512 0.5 20260921 9269 20000000`;
`cd adversarial && ./antsim run out/attack_d_final.cfg`;
`cd exhaustive && python3 naive.py 237232 <k5 max cells>`.
All outputs matched the values used above.
