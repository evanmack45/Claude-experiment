# Langton's Ant: what is PROVEN, what is OPEN, and where the numbers come from

Compiled 2026-09-19 by the literature agent. Purpose: give the movie a list of
claims that are safe to make, with sources, and a list of claims to avoid.

Verification levels used below:

* **VERIFIED** – I fetched and read the primary source itself (HTML, JSON metadata
  API, or PDF text extracted with `extract_pdf_text.py`), and the quote is verbatim
  from it (word spacing in PDF-extracted quotes was restored by hand; wording untouched).
* **SECONDARY** – the primary source is paywalled/unreachable from this sandbox; the
  claim rests on a reputable secondary source that I did read (Wikipedia wikitext,
  MathWorld, a refereed paper citing it, Crossref metadata).
* **UNVERIFIED** – I could not read any source that states it; treat as hearsay.

Everything numeric that I computed myself is in `data/check_oeis_output.json`
(reproduce with `python3 check_oeis.py`; see README.md).

---------------------------------------------------------------------------

## 1. Who introduced the ant, and when

**VERIFIED.** Christopher G. Langton, "Studying artificial life with cellular
automata", *Physica D: Nonlinear Phenomena* 22 (1–3), pp. 120–149, October 1986,
doi:10.1016/0167-2789(86)90237-X.

* Metadata verified via Crossref: https://api.crossref.org/works/10.1016/0167-2789(86)90237-X
  (title, author "Christopher G. Langton", vol. 22, issue 1-3, pp. 120-149, October 1986).
* Full text read from the scan at https://gwern.net/doc/cs/cellular-automaton/1986-langton.pdf
  (OCR layer; header reads "Physica 22D (1986) 120-149 North-Holland, Amsterdam / STUDYING
  ARTIFICIAL LIFE WITH CELLULAR AUTOMATA / Christopher G. LANGTON, Department of Computer and
  Communication Sciences, The University of Michigan, Ann Arbor").

What Langton actually wrote (section on "virtual ants", p. 134–136), verbatim:

> "Plate 6 shows a solitary 'virtual ant' (which we will call a vant) residing in a quiescent
> background. [...] Vants reside in an environment that consists of uniformly spaced, fixed
> cells that are in one of two states (either blue or yellow in the following figures). A vant
> travels in a straight line in empty space. If it encounters a blue cell, it turns right and
> leaves the cell colored yellow. If it encounters a yellow cell, it turns left and leaves the
> cell colored blue. Thus, the vant leaves a 'trail', wherever it goes."

> "Even for the case of a solitary vant, the resulting behavior is quite complex. Plate 7 shows
> the path followed by a single vant when started in a uniform environment of even (blue) fixed
> cells. [...] Thus it is, in fact, operating as a virtual Turing machine."

> "Several other interesting behaviors have been discovered for solitary vants. Plate 8 shows a
> vant that has settled down into building a periodic, self-limited pathway. Once a vant enters
> into such a pattern, it will continue constructing it indefinitely, unless it runs into some
> other pattern in the array. After I demonstrated these vants at the Evolution, Games, and
> Learning conference at Los Alamos National Laboratory, Jim Propp of Berkeley [25] discovered
> a solitary vant behavior that is reminiscent of web-building (plate 9)."

Facts for the movie:
* Langton (1986) called them **"vants"** (virtual ants). His version is implemented inside a
  cellular automaton where the vant is a V-shaped structure moving between "uniformly spaced,
  fixed cells"; as a dynamical system on those cells it is exactly the modern rule
  (blue = "even" = white -> turn right; yellow = "odd" = black -> turn left; flip). This
  matches the turn convention in CONVENTIONS.md (white -> right, black -> left).
* Langton's paper contains **no step count** (no "10,000"), **no "104"**, and does not use the
  word "highway"; the closest statement is "a periodic, self-limited pathway" (Plate 8). Do not
  attribute the number 10,000 or the word "highway" to Langton 1986.
* Langton was at the University of Michigan at the time (paper header), not yet at the Santa
  Fe Institute. (Wikipedia "Christopher Langton", SECONDARY: born 1948/49; organized the first
  Artificial Life workshop at Los Alamos in 1987; later joined SFI.)
* SECONDARY: A. K. Dewdney's *Scientific American* "Computer Recreations" column (Sept. 1989,
  "Two-dimensional Turing machines and tur-mites make tracks on a plane") popularised the ant
  and coined "turmite"; cited as [Dew89] in Lutfalla 2025 (arXiv:2506.10482), not read directly.

## 2. The highway: period 104, displacement, and when it starts

### 2a. Period and displacement (VERIFIED, several independent sources)

* MathWorld, "Langton's Ant", https://mathworld.wolfram.com/LangtonsAnt.html (read):
  > "When the ant is started on an empty grid, it eventually builds a 'highway' that is a series
  > of 104 steps that repeat indefinitely, each time displacing the ant two pixels vertically and
  > horizontally."
* Wikipedia "Langton's ant" (wikitext fetched, read):
  > "Emergent order. Finally the ant starts building a recurrent 'highway' pattern of 104 steps
  > that repeats indefinitely."
* Lutfalla, "The LLLR generalised Langton's ant", arXiv:2506.10482 (2025) (HTML read):
  > "It was conjectured that the same asymptotic behaviour, the highway of period 104 and drift
  > (±2,±2), is reached from any initial configuration with a finite number of non-zero cells."
* Etse, "How Long Can the Escaping Ant Be Confined?", arXiv:2606.26677 (June 2026) (HTML read):
  > "the ant advances indefinitely along one of the four diagonal directions, tracing a periodic
  > pattern of period 104 known as the highway."
* J. P. Boon, "How fast does Langton's ant move?", *J. Stat. Phys.* 102 (1–2), 355–360 (2001),
  doi:10.1023/A:1026581213671 (Crossref metadata verified; arXiv:cond-mat/0004331 abstract read):
  the highway "speed of the ant (c = sqrt(2)/52) follows exactly". Consistency check (mine):
  |(2,2)|/104 = 2*sqrt(2)/104 = sqrt(2)/52. So "2 cells diagonally per 104 steps" and Boon's
  speed are the same statement.
* Our own run (research/results/onset.json, not mine): period 104, displacement (-2,-2) per
  period from the empty grid with the CONVENTIONS start (origin, facing North).
  Direction depends on the start heading and on the mirror convention; literature says
  "southwesterly" for the Gale et al. start (ant heading west into the central cell).

### 2b. When the highway starts: the three numbers seen in the literature

| figure | where it appears | what it means |
|---|---|---|
| "about 10,000" | Gale–Propp–Sutherland–Troubetzkoy 1995; Gajardo–Moreira–Goles 2002; Wikipedia; Etse 2026; Lutfalla 2025 | a rounded description of the end of the chaotic phase, never a precise definition |
| **9977** | OEIS A261990 (2015); Tokarz arXiv:1807.08789 (2018); langtonsant.es | the exact onset of the 104-periodic turn/colour sequence: 9977 steps completed, periodic from step 9978 on |
| 10647 | MathWorld | **not an onset at all**: it is the step count of a figure snapshot ("after 386 (left figure) and 10647 (right figure) steps") |

Verbatim:

* Gale, Propp, Sutherland, Troubetzkoy, "Further travels with my ant", *Math. Intelligencer*
  17(3), 48–56 (1995), arXiv:math/9501233 (PDF text extracted, VERIFIED):
  > "These central symmetries stop occurring eventually and after about 10,000 time-units the
  > ant settles into a periodic 'highway-building' behavior, heading off to infinity in a
  > southwesterly direction. This phenomenon of 'transient symmetry' awaits a satisfying
  > explanation."
* Gajardo, Moreira, Goles 2002 (arXiv:nlin/0306022 v2 text extracted, VERIFIED):
  > "a single ant, starting with all cells in to-left state, has a more or less symmetric
  > trajectory in the first 500 steps; then it goes seemingly randomly for about 10,000 steps,
  > until it suddenly starts building an infinite diagonal 'highway' (a periodic motion with drift)."
* Wikipedia (VERIFIED wikitext): "The ant traces a pseudo-random path until around 10,000 steps."
* OEIS A261990, "Color of the cell Langton's Ant touches on its n-th step before the color is
  changed by the ant; 0=white, 1=black", Aaron David Fairbanks, Sep 07 2015,
  https://oeis.org/A261990 (page read; b-file downloaded and compared, VERIFIED):
  > "The sequence begins repeating at the 9977th step, in a cycle of length 104."
* Tokarz, "Dynamics of Langton's ant allowed to periodically go straight", arXiv:1807.08789
  (2018) (ar5iv HTML read, VERIFIED):
  > "Starting from a blank configuration the highway begins after s_h = 9977 steps."
  > "the ant starts to build a 'highway' – an infinite patterned strip in a diagonal direction
  > with periodicity τ_h = 104 steps."
* MathWorld (VERIFIED): "The plots above show the ant starting from a completely white grid
  after 386 (left figure) and 10647 (right figure) steps."

### 2c. Reconciliation with our own onset (COMPUTED, `python3 check_oeis.py`)

I simulated the ant with the CONVENTIONS.md rule (origin, facing North, white->right) for
10,289 steps and compared the colour read at each step with the OEIS A261990 b-file
(offset 0, n = 0..10288):

* mismatches between b(n) and the colour read at step n+1: **0** (so OEIS's a(n) is the
  colour read at CONVENTIONS step n+1; the OEIS sequence is 0-indexed and its start
  orientation is equivalent to ours up to symmetry);
* smallest n from which b(n) == b(n+104) for the whole rest of the b-file: **9977**;
* therefore in CONVENTIONS.md language: onset step **s = 9977** (9977 steps completed before the
  periodic regime; step 9978 is the first step of the periodic turn sequence). Check:
  t[9977] = 'L' but t[9977+104] = 'R', while t[9978] = t[10082] = 'L'.
* This agrees with research/results/onset.json (`onset_step_s: 9977`, computed independently by
  the onset agent with a C simulator). The alternative reading "first periodic step" gives 9978;
  the OEIS phrase "at the 9977th step" is 0-indexed and means the same thing as s = 9977.
* Caveat on symmetry: the ant's behaviour from an empty grid is the same up to rotation/
  reflection for any start heading, so 9977 does not depend on the initial heading; the
  highway *direction* does.

Safe sentence for the movie: "From an empty grid the ant behaves chaotically for 9,977 steps;
from step 9,978 on it repeats a 104-step cycle for ever, moving two cells diagonally each cycle."
Do NOT say "exactly 10,000", and do NOT cite 10,647 as an onset.

## 3. The unboundedness theorem ("Cohen–Kong theorem")

### 3a. Statement and correct attribution

**VERIFIED statement (from three refereed papers):**

* Gale–Propp–Sutherland–Troubetzkoy 1995 (arXiv:math/9501233, text extracted):
  > "The only general statement that can be made is the following Fundamental Theorem of
  > Myrmecology (Bunimovich–Troubetzkoy): An ant's track is always unbounded. (For a proof see
  > [1]. Note that the attribution given there is incorrect; the proof actually first appeared
  > in [3].)"
  where [1] = D. Gale, "The Industrious Ant", *Math. Intelligencer* 15(2), 54–58 (1993) and
  [3] = L. A. Bunimovich and S. Troubetzkoy, "Recurrence properties of Lorentz Lattice Gas
  Cellular Automata", *J. Stat. Phys.* 67, 289–302 (1992).
* Gajardo–Moreira–Goles 2002 (text extracted):
  > "There are very few results concerning the dynamics of the ant. The main one says that for
  > any initial configuration, the trajectory of the ant is unbounded [2]. This has been
  > generalized to the following: the set of cells that are visited infinitely often by the ant
  > (for a given initial configuration) has no corners [19]. A corner of a set is a cell where at
  > least two neighbors are not in the set, and these are not opposite to each other.
  > Unfortunately, it doesn't tell us anything else about the behavior of the ant in the long term."
  [2] = Bunimovich–Troubetzkoy 1992; [19] = S. Troubetzkoy, "Lewis–Parker Lecture 1997: The Ant",
  *Alabama Journal of Mathematics* 21(2) (1997) (listed on Troubetzkoy's own publication page as
  "The Lewis-Parker lecture: The ant, Alabama J. Math. 21 (1997) 3-15", read at
  https://www.i2m.univ-amu.fr/perso/serge.troubetzkoy/pubs.html).
* Wikipedia (wikitext, VERIFIED): "It is only known that the ant's trajectory is always unbounded
  regardless of the initial configuration [Bunimovich & Troubetzkoy 1992] – this result was
  incorrectly attributed and is known as the Cohen-Kong theorem [Stewart 1994]."

**Bibliographic record of the primary paper (VERIFIED via Crossref
https://api.crossref.org/works/10.1007/BF01049035 and Troubetzkoy's publication page):**
L. A. Bunimovich and S. E. Troubetzkoy, "Recurrence properties of Lorentz lattice gas cellular
automata", *Journal of Statistical Physics* 67 (1–2), 289–302, April 1992, doi:10.1007/BF01049035.
The paper itself is paywalled (Springer redirected to a login page), so I could NOT read its
text; the theorem's presence in it rests on the three refereed citations above (SECONDARY for
the content, VERIFIED for the bibliographic data). Search-engine snippet of the abstract
(UNVERIFIED wording): "We study the recurrence properties of a point particle moving on a regular
lattice randomly occupied with scatterers for strictly deterministic, nondeterministic, and
purely random scattering rules." In that language Langton's ant is the "flipping rotator"
Lorentz lattice gas on the square lattice.

**Precise content of the theorem (my paraphrase of the sources):** for EVERY initial colouring
of the plane (finite or not; the theorem is stated "for any initial configuration"), the ant's
trajectory is not contained in any finite region. Equivalently (Etse 2026, VERIFIED quote):
"the ant's trajectory is always unbounded (non-periodic). Consequently, the ant escapes any
finite connected domain in a finite number of steps."

### 3b. The name "Cohen–Kong"

* SECONDARY. The name comes from Ian Stewart's column "The Ultimate in Anty-Particles",
  *Scientific American* 271(1), 104–107, July 1994, doi:10.1038/scientificamerican0794-104
  (metadata verified on scientificamerican.com; text not readable: the PDF mirror at
  dev.whydomath.org resets the connection and web.archive.org is blocked from this sandbox).
  Wikipedia's external-links section says of it: "Contains the proof that Langton's ant is
  unbounded." Wikipedia links "Cohen" to E. G. D. Cohen (Rockefeller University).
* INFERRED (not stated verbatim by any source I read): "Kong" is X. P. Kong, Cohen's co-author
  on Lorentz-lattice-gas papers (e.g. X. Kong, E. Cohen, "Diffusion and propagation in a
  triangular Lorentz lattice gas cellular automata", *J. Stat. Phys.* 62 (1991) 737, which is
  reference [14] of Gajardo et al. 2002). Cohen and Kong studied the identical model under the
  name "flipping rotator"; the proof, however, was first published by Bunimovich and Troubetzkoy.
* Spelling: MathWorld has a page "Cohen-Kung Theorem" (https://mathworld.wolfram.com/Cohen-KungTheorem.html,
  read: "A theorem that guarantees that the trajectory of Langton's ant is unbounded", no
  references) and Tokarz 2018 also writes "Cohen-Kung". Wikipedia writes "Cohen-Kong".
  For the movie: say "the Bunimovich–Troubetzkoy theorem (often called the Cohen–Kong theorem)".

### 3c. The proof idea (the corner-cell argument)

SECONDARY (the argument as popularised by Stewart; quoted verbatim from Martin & Schuermann,
"Langton's Ant" (2017), https://lucasschuermann.com/writing/langtons-ant, which footnotes it to
Stewart's Gresham lecture "Travels with my ant" and to Troubetzkoy's 1997 Lewis–Parker lecture):

> "It is easy to check that the Theory of Everything for Langton's Ant is time-reversible. That
> is, the current pattern and heading determines the past uniquely as well as the future. Any
> bounded trajectory must eventually repeat the same pattern, position, and heading; and by
> reversibility such a trajectory must be periodic, repeating the same motions indefinitely. Thus
> every cell that is visited must be visited infinitely often. The ant's motion is alternately
> horizontal and vertical, because its direction changes by ±90° at each step. Call a cell an
> H-cell if it is entered horizontally, and a V-cell if it is entered vertically. The H- and
> V-cells tile the grid like the black and white squares of a checkerboard. Select a square M
> that is visited by the ant, and is as far up and to the right as possible, in the sense that
> the cells immediately above and to the right of it have never been visited. Suppose this is an
> H-cell. Then M must have been entered from the left and exited downward, and hence must have
> been white. But M now turns black, so that on the next visit the ant exits upwards, thereby
> visiting a square that has never been visited. A similar problem arises if M is a V-cell.
> This contradiction proves that no bounded trajectory exists."

In one movie-sized sentence: *if the ant stayed in a box for ever, look at the top-right corner
cell it visits; every visit flips that cell, so on alternate visits it must leave through the
top or the right, i.e. outside the box — contradiction.* (Which pair of exits is forced depends
on the turn convention; the structure of the argument does not.)

Troubetzkoy's strengthening (SECONDARY via Gajardo et al. 2002 and Etse 2026): the set of cells
exited infinitely often contains no corner cell, "a corner of a set is a cell where at least two
neighbors are not in the set, and these are not opposite to each other."

## 4. Gale, Propp, Sutherland, Troubetzkoy 1995, "Further travels with my ant"

**VERIFIED.** D. Gale, J. Propp, S. Sutherland, S. Troubetzkoy, "Further travels with my ant",
*The Mathematical Intelligencer* 17(3), 48–56 (1995), doi:10.1007/BF03024370 (Crossref:
published under the column title "Mathematical entertainments", January 1995 issue date;
arXiv:math/9501233, submitted 19 Jan 1995; reprinted as ch. 18 of D. Gale, *Tracking the
Automatic Ant*, Springer 1998).

Abstract (arXiv, verbatim): "We discuss some properties of a class of cellular automata sometimes
called a 'generalized ant'. This system is perhaps most easily understood by thinking of an ant
which moves about a lattice in the plane."

What it establishes (from the extracted text):
* Defines **generalized ants** by a rule-string of L's and R's over n cell states ("If in the
  rule-string we replace an L by a 1 and an R by 0 we see that each ant corresponds to a positive
  integer expressed in base two, so the simple ant is ant 2 and our seven-state ant with 'genome'
  LLRRRLR is ant 98"); Langton's ant is "ant 2" = rule string LR/RL.
* Reports Propp's observation (from Gale & Propp, "Further Ant-ics", *Math. Intelligencer*
  16(1), 37–42, 1994): "Propp finds that different ants behave very differently depending on their
  rule-strings. Some seem to be completely chaotic, while others eventually build highways."
* States the Fundamental Theorem of Myrmecology (unboundedness) with the attribution
  correction quoted in §3a. NB: the theorem as stated there is for Langton's ant; the Stony Brook
  companion page (https://www.math.stonybrook.edu/~scott/ants/, read) adds: "if there is at least
  one L and at least one R in the rule string, the track of the ant will always be unbounded."
* Main new result: the **recurrent bilateral symmetry theorem** for ants LRRL (ant 9) and LLRR
  (ant 12) and more generally for rule strings with the "even run-length property": "In general
  we say a rule-string has the even run-length property if in the cyclic order it consists of
  alternate runs of L's and R's of even length." The proof uses Truchet tiles and the Jordan
  curve theorem ("the 'breakthrough' was made possible by drawing the right picture").
* It does **not** state the highway conjecture, and it does not prove anything about highways.
  It explicitly calls the transient symmetry of Langton's ant "still unexplained".

## 5. Gajardo, Moreira, Goles 2002, "Complexity of Langton's ant"

**VERIFIED.** A. Gajardo, A. Moreira, E. Goles, "Complexity of Langton's ant", *Discrete Applied
Mathematics* 117 (1–3), 41–50, March 2002, doi:10.1016/S0166-218X(00)00334-6 (Crossref verified;
arXiv:nlin/0306022, PDF text extracted; publisher PDF at
https://www.dim.uchile.cl/~anmoreir/oficial/langton_dam.pdf returned 403 here).

Abstract (verbatim): "The virtual ant introduced by C. Langton has an interesting behavior, which
has been studied in several contexts. Here we give a construction to calculate any boolean
circuit with the trajectory of a single ant. This proves the P-hardness of the system and
implies, through the simulation of one dimensional cellular automata and Turing machines, the
universality of the ant and the undecidability of some problems associated to it."

Exactly what is proven (conclusions section, verbatim):
> "The system is P-hard, in the sense that it admits a P-hard problem. The P-hard problem that
> was shown is associated with initial configurations with finite support."
> "The system is capable of universal computation. In spite of being a rather weak notion of
> universality (which requires an infinite – but finitely described – configuration), it shows
> that the dynamics of the system is highly unpredictable."
> "A direct consequence of the previous point is the existence of undecidable problems. We
> notice that this result refers to problems associated with initial configurations with
> infinite support."
> "On the other hand, the decidability of problems whose input is a configuration with finite
> support remains an open question. A positive answer would be given if the conjecture stated in
> 1.2 is found to be true."

The P-hard problem (verbatim): "(P) Given a finite initial configuration of Z², a given initial
position of the ant and a cell. Does the ant ever visit [it]?" reduced from the P-complete
circuit-value problem "(B) Given a boolean circuit (BC) and a truth assignment. Does the truth
assignment satisfy (BC)?" The reduction is "computable using a logarithmic amount of space".

Nuances for the movie:
* The paper proves **P-hardness**, not P-completeness (membership in P is not shown; the authors
  even say "P-hardness is far from being a tight lower bound"). Popular summaries say
  "P-complete"; say "P-hard" (or "at least as hard as any polynomial-time problem to predict").
* "Universal"/"Turing complete" holds only with an **infinite (periodic) initial configuration**.
  Lutfalla 2025 (arXiv:2505.05426, HTML read) makes the same point: universal computation "is
  done by drawing a particular infinite initial configuration, which has no implications on the
  question about the highway".
* Wikipedia's "In 2000, Gajardo et al." refers to the preprint year; the journal paper is 2002.

## 6. Status of the highway conjecture: OPEN

Conjecture (Gajardo et al. 2002, verbatim, VERIFIED): "For any initial configuration with finite
support, the ant eventually starts building the periodic highway, in some unobstructed
direction. (Here, a configuration is said to have finite support if all but a finite number of
cells are in the same state)."

Sources saying it is open, newest first (all read):
* Etse, arXiv:2606.26677 (June 2026): "Numerical simulations consistently show that this highway
  emerges from any finite initial configuration [...], yet this experimental observation has
  never been formally established."
* Lutfalla, "Sideways on the highways", arXiv:2505.05426 (2025): "little progress has been made
  towards proving or disproving this conjecture."
* Gajardo, Lutfalla, Rao, "Ants on the highway", *Natural Computing* 24, 497–509 (2025),
  doi:10.1007/s11047-025-10018-9, arXiv:2409.10124 (HTML read): the conjecture "seems to appear
  on every simulation" and "until now, no simulation suggest the conjecture might be false."
* Wikipedia (wikitext): "All finite initial configurations tested eventually converge to the
  same repetitive pattern, suggesting that the 'highway' is an attractor of Langton's ant, but
  no one has been able to prove that this is true for all such initial configurations."
* MathWorld: "It is believed that no matter what initial pattern the ant is started on, it will
  eventually build a highway (although it might in principle take an extremely long time to
  reach this point). This would appear to follow naturally from the fact that Langton's ant is
  reversible, although it remains formally unproved (Beermann and Van Foeken)."
  (The "would appear to follow from reversibility" clause is NOT a valid argument — see §8.)
* Gajardo et al. 2002: "it is conjectured" (quoted above); "the decidability of problems whose
  input is a configuration with finite support remains an open question."
* Martin & Schuermann 2017 list three open problems: "Is the set of cells that are visited
  infinitely often always empty? Does the ant always turn a finite number of times around the
  origin? Does the ant always build a highway, eventually? The third conjecture implies the
  first two. These conjectures have held for all finite initial configurations tested so far,
  but they remain unproven."

Partial results and related theorems (what IS known):
* Unboundedness for every initial configuration (§3) — "unbounded but not necessarily highway".
* No-corner theorem for the infinitely-often-exited set (Troubetzkoy 1997; §3a).
* Recurrent bilateral symmetry for even-run-length generalized ants (Gale et al. 1995; §4) —
  those ants provably return to the origin infinitely often, so they provably do NOT build a
  highway; the highway conjecture is specific to Langton's LR ant.
* Triangular lattice (SECONDARY, abstract read at arXiv:cond-mat/9905168): P. Grosfils, J. P. Boon,
  E. G. D. Cohen, L. A. Bunimovich, "Propagation and organization in lattice random media",
  *J. Stat. Phys.* 97, 575–608 (1999): for the flipping-rotator ant on the **triangular** lattice
  they prove propagation "regardless of the precise state of the medium" with average velocity
  1/8 — i.e. the highway-type result is a theorem on the triangular lattice, not on the square one.
* Etse 2026 (arXiv:2606.26677): quantitative escape bounds on the square lattice: an n×n domain
  is escaped within (n+1)! steps; height-2 rectangles within 6(n−1) steps (tight); height-3 within
  10n−4. Exact maxima S(n,n) for confined n×n grids (n=1..9): 1, 6, 17, 46, 85, 164, 262, 488, 679
  (Etse's paper "corrects and extends" OEIS A282425, whose current terms read 0, 5, 16, 45, 84,
  163, 261, 487, 678 — every term is exactly 1 less than Etse's S(n,n); I infer a different
  counting convention (moves made inside the grid vs. steps until the exit), not a disagreement).
* Generalized ants (Gajardo–Lutfalla–Rao 2025, Lutfalla 2025a,b): some rules have infinitely many
  distinct highways; LLLR has two highways (periods 52 and 156); LLRRRL and LLRLRLL have
  non-highway emergent behaviours from finite configurations. These "limit" any generalized
  form of the conjecture but say nothing against it for Langton's LR ant.
* Our own computations in this repo (research/results/*.json; not mine, reported for
  reconciliation only): every one of the 2^(k·k) configurations in k×k boxes for k=1..5 and all
  400,000 random configurations tested reached the certified 104-highway. This is evidence, not
  proof, exactly as the literature says.

## 7. Records: longest known transient before a highway

* Empty grid: 9977 steps (§2c). This is the only precisely documented figure for Langton's ant
  in the literature I could read.
* I found **no published record** of a longest transient for Langton's LR ant from a finite
  non-empty configuration. Searches for "longest transient / record" return only the 9977
  figure and results for other rules. So do not claim "the longest known transient is X".
* For OTHER rule strings there are published long transients (SECONDARY, search snippet of
  Gajardo–Lutfalla–Rao 2025 / Lutfalla 2025, not checked line by line): "The 41-ant creates a
  highway after 280,085,922 steps" and "the 99-ant starts a highway after 100,365,745 steps";
  Tokarz 2018 (abstract, VERIFIED) reports modified ants "exhibit a long-term chaotic behavior,
  exceeding even 10^13 steps" — but these are NOT Langton's ant.
* The repo's own random sweep found an onset of 196,974 steps (k=64, p=0.75, seed 20260919,
  sample 4491; research/results/random_longest.json). That is a local computational record,
  not a literature record; present it as "the longest we found", never as "the longest known".
* Related but different quantity: confinement time in an n×n box (Etse 2026 / OEIS A282425), see §6.

## 8. Misconceptions to avoid in the video

1. **"Langton proved/found the highway in 1986."** Langton introduced the vant and noted a
   "periodic, self-limited pathway" (Plate 8), but the 10,000-step description, the number 104,
   and the name "highway" come from later work (Gale 1993; Gale & Propp 1994; Stewart 1994).
2. **"It is proven that the ant always builds a highway."** Open. Proven: unbounded (§3).
3. **"The Cohen–Kong theorem was proved by Cohen and Kong."** The proof was first published by
   Bunimovich and Troubetzkoy (1992); the name is a mis-attribution that stuck (Gale et al. 1995
   say so explicitly). Spelling varies (Kong/Kung).
4. **"Unbounded therefore highway."** Unboundedness does not imply periodic motion; the ant could
   in principle wander without ever becoming periodic. Gajardo et al.: the theorem "doesn't tell
   us anything else about the behavior of the ant in the long term."
5. **"The highway follows from reversibility."** (MathWorld phrasing.) Reversibility only shows
   a bounded orbit would be periodic; it is used in the *unboundedness* proof, and says nothing
   about highways. Do not repeat it.
6. **"Langton's ant is Turing complete"** without qualification. It is universal only with an
   infinite, periodic initial configuration; on finite configurations the known result is
   P-hardness of the cell-reachability problem, and decidability there is open (Gajardo et al.).
7. **"P-complete."** The paper proves P-hard; membership in P was not shown.
8. **"The highway appears after exactly 10,000 steps."** 9977 (see §2). "About 10,000" is fine.
9. **"After 10,647 steps the highway starts."** 10,647 is a MathWorld figure caption, not an onset.
10. **"The ant is chaotic."** Its transient is *pseudo-random-looking*; the system is
    deterministic and reversible. Say "looks random", not "is random"/"is chaotic" (the papers
    say "seemingly random", "apparently erratic").
11. **"The highway always goes south-west / up-right."** The direction depends on the start
    heading and mirror convention; from the empty grid all four diagonals occur across
    symmetric starts (our random sweep saw all four directions roughly equally).
12. **"Every simulation ever run reached the highway, so it is basically proven."** Correct
    as evidence, but the sources are careful: "no simulation suggest the conjecture might be
    false" (Gajardo–Lutfalla–Rao) is not a proof, and generalized ants (LLLR, LLRRRL) show
    that intuition about "unique highway" can fail for close cousins of the rule.
13. **Turn convention.** Wikipedia/MathWorld state the rule as "white: turn right/left"
    inconsistently across sources (MathWorld: black->right, white->left; Wikipedia and
    CONVENTIONS.md: white->right, black->left). Both are the same system up to reflection;
    just be consistent within the film.

## 9. Source list (with what I could verify)

| # | Source | Level | URL |
|---|---|---|---|
| S1 | Langton 1986, Physica D 22:120–149 | VERIFIED (Crossref + OCR text) | https://api.crossref.org/works/10.1016/0167-2789(86)90237-X ; https://gwern.net/doc/cs/cellular-automaton/1986-langton.pdf |
| S2 | Bunimovich & Troubetzkoy 1992, J. Stat. Phys. 67:289–302 | VERIFIED metadata; content SECONDARY | https://api.crossref.org/works/10.1007/BF01049035 ; https://link.springer.com/article/10.1007/BF01049035 |
| S3 | Gale 1993, "The Industrious Ant", Math. Intell. 15(2):54–58 | SECONDARY (cited by S4, MathWorld) | (paywalled) |
| S4 | Gale & Propp 1994, "Further Ant-ics", Math. Intell. 16(1):37–42 | SECONDARY (cited by S5, MathWorld) | (paywalled) |
| S5 | Gale, Propp, Sutherland, Troubetzkoy 1995, Math. Intell. 17(3):48–56 | VERIFIED (arXiv PDF text) | https://arxiv.org/abs/math/9501233 ; https://api.crossref.org/works/10.1007/BF03024370 |
| S6 | Stewart 1994, Sci. Am. 271(1):104–107 | SECONDARY (metadata verified; text unreachable) | https://www.scientificamerican.com/article/the-ultimate-in-anty-particles/ |
| S7 | Troubetzkoy 1997, Lewis–Parker lecture "The ant", Alabama J. Math. 21(2):3–15 | SECONDARY (listed on author's page; cited by S8, S13) | https://www.i2m.univ-amu.fr/perso/serge.troubetzkoy/pubs.html |
| S8 | Gajardo, Moreira, Goles 2002, DAM 117:41–50 | VERIFIED (arXiv PDF text + Crossref) | https://arxiv.org/abs/nlin/0306022 ; https://api.crossref.org/works/10.1016/S0166-218X(00)00334-6 |
| S9 | Grosfils, Boon, Cohen, Bunimovich 1999, J. Stat. Phys. 97:575–608 | SECONDARY (arXiv abstract) | https://arxiv.org/abs/cond-mat/9905168v1 |
| S10 | Boon 2001, "How fast does Langton's ant move?", J. Stat. Phys. 102:355–360 | VERIFIED metadata + arXiv abstract | https://arxiv.org/abs/cond-mat/0004331 ; https://api.crossref.org/works/10.1023/A:1026581213671 |
| S11 | OEIS A261990 (Fairbanks 2015) + b-file | VERIFIED (page + data recomputed) | https://oeis.org/A261990 ; https://oeis.org/A261990/b261990.txt |
| S12 | OEIS A282425 (Cestnik 2017, ext. 2026) | VERIFIED (page) | https://oeis.org/A282425 |
| S13 | Martin & Schuermann 2017 blog (proof text) | SECONDARY | https://lucasschuermann.com/writing/langtons-ant |
| S14 | Tokarz 2018, arXiv:1807.08789 | VERIFIED (ar5iv HTML) | https://arxiv.org/abs/1807.08789 |
| S15 | Gajardo, Lutfalla, Rao 2025, Natural Computing 24:497–509 | VERIFIED (arXiv HTML) | https://arxiv.org/abs/2409.10124 |
| S16 | Lutfalla 2025, "Sideways on the highways", arXiv:2505.05426 | VERIFIED (HTML) | https://arxiv.org/html/2505.05426v1 |
| S17 | Lutfalla 2025, "The LLLR generalised Langton's ant", arXiv:2506.10482 | VERIFIED (HTML) | https://arxiv.org/html/2506.10482 |
| S18 | Etse 2026, "How Long Can the Escaping Ant Be Confined?", arXiv:2606.26677 | VERIFIED (HTML) | https://arxiv.org/abs/2606.26677 |
| S19 | Wikipedia "Langton's ant" (wikitext, rev. of 2026-09-19) | VERIFIED as a secondary index | https://en.wikipedia.org/wiki/Langton%27s_ant |
| S20 | MathWorld "Langton's Ant" / "Cohen-Kung Theorem" | VERIFIED as a secondary source | https://mathworld.wolfram.com/LangtonsAnt.html ; https://mathworld.wolfram.com/Cohen-KungTheorem.html |
| S21 | Stony Brook ants page (Sutherland) | VERIFIED (read) | https://www.math.stonybrook.edu/~scott/ants/ |
| S22 | Kong & Cohen 1991, J. Stat. Phys. 62:737 | UNVERIFIED (only as ref. [14] of S8) | — |
| S23 | Dewdney 1989, Sci. Am. "Computer Recreations" | UNVERIFIED (only as [Dew89] of S17) | — |

Known reference glitch: Etse 2026 cites "Troubetzkoy, S. Behavior of the Langton's ant. arXiv
math/0006108 (2000)"; that arXiv number is Farber's "Novikov–Shubin signatures, II" (checked at
https://arxiv.org/abs/math/0006108). The intended source is almost certainly the 1997
Lewis–Parker lecture (S7). Do not cite math/0006108.
