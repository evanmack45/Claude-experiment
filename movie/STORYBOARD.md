# STORYBOARD — "Two Rules, One Road" (Langton's Ant and the Highway Conjecture)

**Final director's cut.** Structure of the winning proposal (index 0) with the judge-mandated grafts:
the age-tint "newest ink glows" palette, the turn-stream oscillator and the 104-steps-per-frame
barcode lock (proposal 2); PROVEN/OPEN pills, the real onset histogram, the 60 % contrast cap
in chaos, the three-phase rule animation (proposal 1); the "N tested / N highways / 0 exceptions /
evidence, not a proof" verdict (proposal 2). Every fatal flaw the judges found is fixed in place
(see section 8). Every headline number on screen comes from `research/results/movie_facts.json` (section 6);
the histogram is read from `exhaustive.json`, and the mosaic/wall example patterns are fixed
records the renderer re-simulates and asserts (as built). Every text line below was measured with the real font files (section 2.4).

---

## 1. Title, duration, format, concept

| | |
|---|---|
| **Title** | Two Rules, One Road: The Ant Nobody Can Explain |
| **Duration** | **74.0 s** (2220 frames). Optional +5.0 s "walls" insert (Appendix A) only if obstacle data exists. |
| **Format** | 1080 x 1920 (9:16 vertical), 30 fps, H.264 yuv420p, AAC 192 kbit/s, <= 50 MB, works muted |
| **Author line** | made by Claude (an AI) · github: evanmack45/langtons-ant-highway |

**Concept (one paragraph).** A cold open drops the viewer into a live simulation already mid-chaos;
at t = 0.5 s a perfectly straight road erupts out of the mess and streaks toward the lower-left corner
while the on-screen claim reads "2 rules. Then THIS happens." We then earn it: the two rules are taught
in five seconds with slow, sonified steps (right turn = high pluck, left turn = low pluck), ten thousand
steps of chaos are compressed into six seconds with a spinning counter, the picture freezes on the exact
onset step, and the highway is laid down under a follow-cam, its newest cells glowing amber simply because
they are the newest, while the ant's own turn sequence, read as a waveform, snaps from crackle into a
steady 220 Hz tone. Then the pivot: change the start, any finite start, and every one we tried builds a
road, but nobody can prove it always will. Evidence is shown as things filling up (a 2x3 mosaic of live
runs from real 4x4 patterns, a 256x256 wall of dots for all 65,536 4x4 patterns, the single most stubborn
start we found running live until it too builds a road, a real onset histogram), followed by a
screenshot-able verdict ("466,066 starts tested / 466,066 highways / 0 exceptions / That's evidence.
Not a proof."), a three-line PROVEN / PROVEN / UNPROVEN scorecard, and a call to action that hands the
open problem to the viewer. The last shot mirrors the first so autoplay loops. Claude speaks in first
person exactly once.

---

## 2. Visual style spec

### 2.1 Palette (exact hex)

| Role | Hex | Notes |
|---|---|---|
| Background = white (empty) cell | `#12141B` | CONVENTIONS "white" is rendered DARK for phone legibility. Rule logic unchanged. On-screen words are "empty / marked". |
| Hairline grid | `#1C1F28` | drawn only when cell >= 20 px (1 px gap between cells, `render_grid(gap=True)`) |
| Visited-but-empty cell | `#1A1D26` | faint tint for cells that were flipped at least once and are white again; shown only when cell >= 4 px, off in mosaic tiles and in the dot wall. Makes the "mess" extent readable. |
| Black (marked) cell, old | `#F4EFE3` cream | age >= 1,040 steps since its last flip (10 periods) |
| Black (marked) cell, fresh | `#FFB84D` amber | age < 1,040 steps since its last flip. **This is the only "highway highlight" and it is honest: the road tip glows only because it is the newest ink. Thresholds identical for every run shown.** |
| Ant | `#3D8BFF` blue | filled square (cell < 60 px) or square + heading chevron (cell >= 60 px); soft glow (`draw_ant(glow=(61,139,255))`), min 10 px |
| Ant trail | `#3D8BFF` at 60 % -> 0 % | last 20 ant positions, fading, only when cell >= 4 px |
| Accent (numbers, counters while running, brackets, certified tiles) | `#FFB84D` amber | |
| Counter when frozen | `#F4EFE3` cream | |
| PROVEN pill | `#4CD97B` green fill, text `#0B0D12` | |
| OPEN / UNPROVEN pill | `#FFB84D` amber fill, text `#0B0D12` | |
| Red (any uncertified / cap-hit run; expected: never drawn) | `#FF4D4D` | |
| Text primary | `#F4EFE3` cream | |
| Text secondary (captions, citations, credit) | `#A8A49B` | |
| Text band | `#0B0D12` at 85 % alpha, 24 px corner radius, 28 px padding | every text card sits on a band unless the background is plain `#0B0D12` |
| Plain card background | `#0B0D12` | verdict, scorecard, mystery cards |

Age of a black cell = current step − step of its last flip (maintain a `uint32 last_flip` array
alongside the grid; `render_grid(age=...)` maps age < 1,040 to amber, else cream).

### 2.2 Fonts (full paths)

| Role | File | Sizes (px) |
|---|---|---|
| Hero | `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf` | 104 (hook line 1), 96, 84, 76, 72 |
| Body | `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf` | 60, 56, 52, 48 |
| Mono (counters, numbers, citations, credit, labels) | `/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf` | 104 (onset hero), 64, 60, 48, 44, 40, 38, 36 |
| Pill labels | `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf` | 56 |

Minimums: body >= 48 px, captions/credit >= 36 px mono (only the credit and chart axis labels use 36–40).
Line spacing 1.15. Max 8 words per line. `core.FONTS` already maps `bold`, `regular`, `mono`.

### 2.3 Safe zone

All text, pills, charts, counters and tile borders inside **x 80..960, y 240..1600**. Nothing textual in
the top 240 px, bottom 320 px or right 120 px. The simulation itself may fill the whole frame.
Text bands are centered on x = 520 (the center of the safe zone), NOT on x = 540.

### 2.4 Measured line widths (DejaVu, real files, `ImageFont.getlength`) — must stay <= 880 px

| Line | Font / px | Width px |
|---|---|---|
| 2 rules. | Bold 104 | 441 |
| Then THIS happens. | Bold 76 | 856 |
| Empty cell? / Marked cell? | Regular 60 | 347 / 375 |
| Turn RIGHT, mark it, step. / Turn LEFT, erase it, step. | Regular 56 | 721 / 689 |
| rule 1 of 2 | Mono 40 | 264 |
| That's it. | Bold 96 | 479 |
| The whole program. | Regular 56 | 562 |
| no randomness. no lookahead. | Mono 44 | 741 |
| No pattern. No repeats. | Regular 60 | 705 |
| Deterministic. Looks random. | Regular 56 | 823 |
| Step 9,977. (Step 196,974. worst case) | Mono 104 | 688 (813) |
| The mess is about to end. | Regular 56 | 726 |
| Then: a road. | Bold 96 | 720 |
| 104 steps. Repeats forever. | Regular 56 | 768 |
| 104 turns | Mono 44 | 238 |
| It never turns back. | Bold 72 | 801 |
| No finite start can trap the ant. | Regular 48 | 748 |
| Bunimovich & Troubetzkoy, 1992 | Mono 40 | 722 |
| Nobody can / prove why. | Bold 84 (two lines) | 556 / 516 |
| Change the start. | Regular 56 | 490 |
| Any finite start you like. | Regular 56 | 668 |
| Every one we tried builds a road. | Regular 52 | 859 |
| Nobody can prove it always will. | Regular 52 | 839 |
| Every 4x4 start. All 65,536. | Regular 56 | 766 |
| tested 65,536 / 65,536 | Mono 60 | 794 |
| 65,536 / 65,536 built the road. | Regular 52 | 798 |
| 3x3 box: 512 / 512 | Mono 40 | 433 |
| random, up to 64x64: / 400,000 / 400,000 | Mono 40 | 481 / 409 |
| 5x5 box: 33,554,432 / 33,554,432 (conditional) | Mono 36 | 693 |
| The stubbornest start we found: | Regular 52 | 836 |
| I evolved starts to stall it. (conditional) | Regular 56 | 713 |
| Longest delay: 196,974 steps. | Regular 56 | 841 |
| Still a road. | Bold 84 | 550 |
| onset step, all 65,536 4x4 starts | Mono 36 | 715 |
| 466,066 starts tested. / 466,066 highways. / 0 exceptions. | Mono 64 | 847 / 655 / 500 |
| That's evidence. / Not a proof. | Bold 72 | 664 / 483 |
| PROVEN / UNPROVEN | Bold 56 | 258 / 351 |
| It never gets trapped. / It can run any logic circuit. / It always builds the road. | Regular 56 | 611 / 746 / 704 |
| Bunimovich & Troubetzkoy 1992 / Gajardo, Moreira & Goles 2002 | Mono 40 | 698 / 698 |
| Can YOU find a start / that never / builds a road? | Bold 72 | 822 / 425 / 572 |
| Any finite start counts. / Proof or counterexample? / Argue in the comments. | Regular 48 | 547 / 617 / 578 |
| made by Claude (an AI) | Mono 40 | 529 |
| github: evanmack45/langtons-ant-highway | Mono 36 | 845 |
| step 9,977 · period 104 | Mono 48 | 664 |
| road at step 19,039 | Mono 40 | 457 |

Every line above was measured verbatim with the real font files. The renderer MUST still run a measurement pass over every
string it draws (`font.getlength(line) <= 880`) and shrink that line by 4 px steps until it fits,
logging any shrink. Placeholders with more digits (e.g. a 7-digit LONGEST_ONSET) are covered by the
worst-case column.

### 2.5 Grid rendering rules

| Phase | px per cell | cells across (1080 / px) | Notes |
|---|---|---|---|
| Hook, CTA | 6 | 180 | box-filter downsample, no gaps |
| Rules demo | 120 | 9 | 1 px grid gaps, chevron ant, nearest-neighbour, no anti-aliasing |
| Zoom-out (S04) | 120 -> 40 | 9 -> 27 | smoothstep |
| Chaos (S05) | 40 -> 12 | 27 -> 90 | continuous, ease-out |
| Freeze (S06) | 12 -> 12.24 | 90 -> 88.2 | 2 % push-in over 4 s |
| Road follow-cam (S07a) | 10 | 108 | camera locked on ant |
| Pull-back / infinity (S07b, S08) | auto: `cells_across = clamp(1.25*(abs(ant_x - blob_cx) + 60), 108, 1080)` | 108 -> ~1040 | center = midpoint(ant, blob center); road drawn min 2 px wide when cell < 2 px |
| Mosaic tiles | 3.6 (360 px tile / 100 cells) | 100 per tile | no visited tint, no trail |
| Longest run (S12) | auto-fit bbox of modified cells: `cells_across = clamp(1.3*max(bw, bh*0.5625, 64), 64, 1080)`, bbox smoothed with 0.3 s lag | | |
| Scorecard background | 8 | 135 | 25 % opacity |

Rendering: `render_grid` at integer cell sizes >= 4 px with nearest-neighbour; below 4 px render at 4x
and downsample with `Image.BOX` so the road reads as a solid diagonal band; the road (a 7-cell-wide
strip) must never be thinner than 2 px on screen. **Photosensitivity cap:** whenever more than 100 steps
are drawn per frame (S05 from ~13.3 s, S08, S10, S12), blend black cells 40 % toward the background
(60 % contrast) for the churning region; the amber age tint is applied after the blend.

Simulation grid: use `core.simulate(..., size=2048)` for the empty-grid run (the ant reaches
x ≈ −800 by 33 s) and `size=4096` for the longest-delay run (its bbox is unknown until
`movie_facts.json` is read; assert `max_abs_coord + 64 < size/2`, else re-run with 8192).

Ant marker: `draw_ant` (heading triangle) when cell >= 60 px; filled square with glow otherwise;
minimum 10 px. Ant is always drawn on top of text-free regions; text bands are drawn on top of the ant.

### 2.6 Motion language

- Hard cuts between chapters (S01->S02, S08->S09, S09->S10, S10->S11, S11->S12, S12->S13, S13->S14, S14->S15).
- Camera pans and zooms inside a shot use `smoothstep` unless a shot says otherwise; the "to infinity"
  pull-back uses the auto rule above (which is exponential-like in on-screen cell size).
- Text: fade in 150 ms with a 12 px upward drift, fade out 150 ms (`fade(t, t0, t1, 0.15, 0.15)`).
  Every card >= 2.0 s on screen at full opacity. Hero "slams" (S01, S06, S12 "Still a road.") are
  1-frame snaps with no fade-in.
- Counters: DejaVu Sans Mono, tabular, amber while running, cream when frozen, formatted with
  thousands separators ("step 9,977").
- Pills: 56 px bold label on a rounded rect (radius 28, padding 20 x 8), placed left of or above the line.

---

## 3. Shot list

Coordinates: x East, y North (CONVENTIONS). On screen, +y is UP, so the empty-grid highway
(direction −x,−y) travels toward the **lower-left** corner. `{PLACEHOLDERS}` are defined in section 6.
"Empty-grid run" = one `AntRun` from the empty grid, simulated to >= 60,000 steps, shared by S01,
S04–S08, S14, S15 via `GridPlayer.seek`. Times are seconds from the first frame; frame = round(t*30).

### 3.1 Step schedule for the empty-grid run (frame-exact; precompute `step_at_frame[]` once)

| Shot | t | steps/s | step at start -> end |
|---|---|---|---|
| S01 | 0.0–2.0 | 3,000 | {ONSET_STEP}−1,500 -> {ONSET_STEP}+4,500 (onset frame = frame 15, t = 0.5) |
| S02 | 2.0–4.5 | 2 | step k fires at t = 2.3 + 0.5(k−1), k = 1..4 |
| S03 | 4.5–7.0 | 2 (0.4 s hold first) | step 5 at 4.9; steps 6–9 at 5.4, 5.9, 6.4, 6.9 |
| S04 | 7.0–10.0 | 2 -> 60, exponential: r(t) = 2·30^((t−7)/3) | 9 -> 60 |
| S05 | 10.0–16.0 | 60 -> ~8,130, exponential: r(t) = 60·e^(a(t−10)), a solved so ∫ = {ONSET_STEP}−60 (a = 0.8183 for 9,977) | 60 -> {ONSET_STEP} **exactly on frame 480** |
| S06 | 16.0–20.0 | 0 | {ONSET_STEP} |
| S07 | 20.0–27.0 | 3,120 (= 104 per frame) | -> {ONSET_STEP}+21,840 |
| S08 | 27.0–33.0 | 3,120 | -> {ONSET_STEP}+40,560 |
| S14 (bg) | 62.0–68.0 | 300 | resumes from {ONSET_STEP}+40,560 |
| S15 | 68.0–74.0 | 3,000 | re-seek to {ONSET_STEP}−1,500 (identical to S01) |

Schedules are integer steps per frame: cumulative float step count, floored per frame, with the
S05 end forced to land on {ONSET_STEP} at frame 480 (distribute rounding into the last 10 frames).

### 3.2 The shots

| id | t (s) | simulation | camera | on-screen text (exact) | text position | audio |
|---|---|---|---|---|---|---|
| **S01 HOOK** | 0.0–2.0 | Empty-grid run resumed at {ONSET_STEP}−1,500, 3,000 steps/s (road advances 57.7 cells/s per axis). Onset at t = 0.5 s; the amber tip streaks toward the lower-left; blob stays put. Step counter spinning. | Static. Center (−25, −25) cells, 180 cells across (6 px/cell). Blob center (5, 0) sits at screen (720, 1110); ant exits the left edge at ~1.9 s so the departure is felt. | L1 `2 rules.` (Bold 104, snaps in at 0.2 s). L2 `Then THIS happens.` (Bold 76, snaps at 0.9 s). Both hold to 2.0. Counter `step 8,477` … (Mono 60, amber). | Band top y = 300, centered x = 520. Counter at y = 1520, left x = 100. | Starts mid-crackle (turn-stream oscillator on aperiodic data, −18 dBFS, 0–0.5 s). On the onset frame: 48 Hz sub thump (250 ms) and the oscillator collapses into the 220 Hz highway tone. Drone A1/A2 (55 + 110 Hz) at −24 dBFS under everything. |
| **S02 RULE 1** | 2.0–4.5 | HARD CUT. Fresh empty grid. Ant at origin facing N (up). Steps 1–4 at 2.3, 2.8, 3.3, 3.8, each in three phases: 120 ms rotate 90° clockwise with a curved amber arrow, 150 ms cell fill (radial wipe to amber = fresh), 180 ms eased slide. Trajectory: (0,0)N -> (1,0)E -> (1,−1)S -> (0,−1)W -> (0,0)N. | Static, center (0.5, −0.5), 9 cells across (120 px/cell), hairline grid on. | `Empty cell?` (Regular 60) / `Turn RIGHT, mark it, step.` (Regular 56, "RIGHT" amber). Label `rule 1 of 2` (Mono 40, secondary). | Band top y = 260. Label at y = 1520, x = 100. | Drone. Per step: 3 ms click at the flip + R pluck = E4 329.6 Hz (decaying sine + 2nd/3rd harmonics at −6/−12 dB, 350 ms). Four identical high plucks. |
| **S03 RULE 2** | 4.5–7.0 | Ant is back on the origin, now marked. Hold 0.4 s with a pulsing amber outline on that cell. Step 5 at 4.9: rotate counter-clockwise (blue-white arrow), cell wipes back to empty (visited tint), slide. Steps 6–9 at 5.4, 5.9, 6.4, 6.9 (turns per real trajectory). | Same static camera. | `Marked cell?` (Regular 60) / `Turn LEFT, erase it, step.` (Regular 56, "LEFT" blue `#3D8BFF`). Label `rule 2 of 2`. | Same as S02. | Step 5: L pluck = A3 220 Hz (same envelope), audibly lower. Steps 6–9 play their real R/L plucks. Viewer has now learned high = right, low = left. |
| **S04 WHOLE PROGRAM** | 7.0–10.0 | Speed ramps 2 -> 60 steps/s (exponential). The little pattern near the origin starts to writhe. | Smoothstep zoom-out 9 -> 27 cells across (120 -> 40 px/cell), center eases to the centroid of modified cells. | `That's it.` (Bold 96) / `The whole program.` (Regular 56) at 7.0–10.0; below: `no randomness. no lookahead.` (Mono 44, secondary). Counter appears at 7.0 and ticks. | Band top y = 300. Counter y = 1520, x = 100. | Plucks follow every step until 20 steps/s (~8.6 s), then crossfade over 0.5 s into the turn-stream oscillator (crackle). Drone adds E (82.4 Hz) as tension. |
| **S05 CHAOS** | 10.0–16.0 | Exponential ramp 60 -> ~8,130 steps/s, solved so the counter reads exactly {ONSET_STEP} on frame 480. Blob grows to ~49 x 45 cells. 60 % contrast cap once > 100 steps/frame. | Continuous ease-out zoom 27 -> 90 cells across (40 -> 12 px/cell), center = centroid of modified cells (smoothed 0.3 s), blob kept inside the middle 60 % of the frame. | Card A 10.0–13.0: `No pattern. No repeats.` (Regular 60). Card B 13.0–16.0: `Deterministic. Looks random.` (Regular 56). Counter spinning, amber, Mono 60. | Band top y = 300. Counter y = 1520. | Turn-stream crackle, level rising −20 -> −16 dBFS. Pad becomes the unresolved cluster A2 + Bb3 + E4 + F4, lowpass cutoff rising 400 -> 2,500 Hz across the shot, detune drifting +8 cents by 16.0. |
| **S06 FREEZE** | 16.0–20.0 | Frozen at {ONSET_STEP}. One frame of white at 6 % opacity on frame 480; a 3-cell amber ring pulses around the ant (ant is at (−15, 10) facing W for the empty grid). Counter turns cream. | 2 % push-in over 4 s toward the ant. | `Step {ONSET_STEP_FMT}.` (Mono 104, cream, snaps on frame 480) / `The mess is about to end.` (Regular 56). Counter frozen `step {ONSET_STEP_FMT}` cream. | Band centered at y = 880 (over the blob). | Crackle cuts to **0.4 s of hard silence** (16.0–16.4), then a single 48 Hz sub thump with a 2 s tail. Drone returns at −30 dBFS at 18.0. |
| **S07 THE ROAD** | 20.0–27.0 | Resumes at 3,120 steps/s = exactly 104 steps per frame (one period per frame). 20.0–24.0: follow-cam; the 40-cell period motif is laid as a braided diagonal ribbon whose newest 10 periods glow amber, the blob slides away up-right. 24.0–27.0: camera lets go and pulls back to reveal blob + straight road leaving toward the lower-left. **Turn strip** (20.0–27.0 only): the last 208 turns as 4 px ticks (R = tick up amber, L = tick down cream) along y 1440–1500, x 100–932; because 104 steps advance per frame the barcode is **frozen**, with an amber bracket over 104 ticks labelled `104 turns` + a drawn loop arrow. | 20.0–24.0: locked on the ant, 108 cells across (10 px/cell). 24.0–27.0: 0.6 s smoothstep hand-off into the auto pull-back rule (center = midpoint(ant, blob), `cells_across = 1.25*(dx+60)`, reaching ~590 cells across by 27.0). | Card A 20.0–23.0: `Then: a road.` (Bold 96). Card B 23.5–27.0: `104 steps. Repeats forever.` (Regular 56). Counter running, amber, suffix ` · period 104` (Mono 48: `step 22,457 · period 104`). | Band top y = 300. Counter y = 1380 (above the strip). | On frame 600 the turn-stream oscillator is on periodic data: a steady 220 Hz tone (A3) with the highway's own timbre, octave-below copy at 110 Hz at −9 dB. Pad snaps to open A major (A2, E3, A3, C#4, E4), cutoff 1,200 Hz, detune 0. A low kick (48 Hz, 120 ms) on every 30th frame (once per second = 30 periods) for a pulse. |
| **S08 TO INFINITY** | 27.0–33.0 | 3,120 steps/s continues. Road reaches ~780 cells; blob shrinks to a thumb-sized smudge in the upper right; the amber tip is a glowing dot leaving the lower-left. Road drawn min 2 px wide. | Auto pull-back rule continues, clamped at 1,080 cells across (1 px/cell) by ~33 s. Center drifts so the blob sits at ~(760, 700) on screen and the road runs to the lower-left corner. | Card A 27.0–30.0: `It never turns back.` (Bold 72). Card B 30.0–33.0: pill `PROVEN` (green) + `No finite start can trap the ant.` (Regular 48) + `Bunimovich & Troubetzkoy, 1992` (Mono 40, secondary). | Band top y = 300; pill left of the line at x = 100. | Tone continues, level rising to −14 dBFS; a white-noise riser (200 Hz -> 8 kHz band-pass sweep, 3 s, −24 dBFS) under card A; pad adds A5/E6 shimmer. A clean bell (A4 880 Hz sine, 2 s decay) on the PROVEN pill at 30.0. |
| **S09 THE MYSTERY** | 33.0–38.0 | HARD CUT to plain `#0B0D12`; the S08 road frame continues behind at 20 % opacity (frozen). 35.5–38.0: a 4x4 box appears centered at (520, 900), 80 px/cell, ant at the origin cell facing up; the box's 16 cells re-roll 6 times (every 0.3 s, real random bits, seeded 20260919) then lock on the 7th pattern. | n/a (box is a UI element). | Card A 33.0–35.5: `Nobody can` / `prove why.` (Bold 84, two lines, centered). Card B 35.5–38.0: `Change the start.` / `Any finite start you like.` (Regular 56). | Card A centered at y = 800. Card B band top y = 300 (above the box). | Everything drops to the bare drone (silence as emphasis). Each re-roll = a short click cluster (5 x 3 ms clicks over 40 ms); the lock = a low wooden knock (150 Hz, 60 ms). |
| **S10 MOSAIC** | 38.0–44.0 | HARD CUT. Six live runs from six REAL 4x4 patterns ({MOSAIC_TILES}), each at 6,000 steps/s, staggered 0.4 s in the order below so certification times ascend; a tile's border turns amber and a label appears at its certification step. Roads exit their tiles in four different diagonal directions. | Six 360x360 tiles at x = {140, 580}, y = {360, 760, 1160}; each tile 100 cells across, centered on its own pattern's modified-cell centroid (lagged), 60 % contrast cap. | Card A 38.0–41.0: `Every one we tried builds a road.` (Regular 52). Card B 41.0–44.0: `Nobody can prove it always will.` (Regular 52). Per tile on certification: `road at step {TILE_ONSET_i}` (Mono 40, amber, inside the tile's bottom edge). | Band top y = 250 (above the tiles). Tiles occupy y 360–1520. | Each tile's crackle mixed at −26 dBFS; at each certification a pentatonic blip ascending in certification order (A4, B4, C#5, E5, F#5, A5) that stays unresolved. On card B the pad thins to a lone A2. |
| **S11 THE COUNT** | 44.0–50.0 | HARD CUT. A 256 x 256 wall of 3 px dots (768 px square) at x 136–904, y 470–1238: one dot per 4x4 pattern, index = config index (bit encoding in `exhaustive.json`). Dots fill amber in index order over 44.0–47.5, rate accelerating 1 -> 2,000 per frame; any pattern not certified is drawn red `#FF4D4D` (expected: none). At 47.5 the completed wall flashes 4 % white and the result line snaps in; side bars slide in at 48.0 and 48.5. | n/a (data viz). | Card A 44.0–47.5: `Every 4x4 start. All 65,536.` (Regular 56). Counter above the wall: `tested 00,000 / 65,536` -> `tested {N4}/{N4}` (Mono 60, amber -> cream). Card B 47.5–50.0: `{N4_HIGHWAY} / {N4} built the road.` (Regular 52). Side bars (Mono 40, secondary): `3x3 box: {N3_HIGHWAY} / {N3}` and `random, up to 64x64:` / `{N_RANDOM_HIGHWAY} / {N_RANDOM}`; a third bar `5x5 box: {N5_HIGHWAY} / {N5}` (Mono 36) ONLY if the 5x5 result is merged (section 6). | Card band top y = 250. Counter y = 390. Side bars at y = 1290, 1360, 1430 (each a 60 px band), left x = 136. | One micro-tick per dot, rate-limited to 200 ticks/s, then a filtered-noise shimmer as the rate exceeds it; the drone climbs stepwise (A2 -> C#3 -> E3). Completion at 47.5 = A major chord hit with a 1.5 s tail. Each side bar = a short slot click. |
| **S12 THE STUBBORNEST START** | 50.0–57.0 | HARD CUT. 50.0–50.6: the longest-delay pattern ({LONGEST_CONFIG}) appears static at 20 px/cell (or auto-fit if its box is > 48 cells). 50.6–57.0: its run plays live at a constant rate r = {LONGEST_ONSET} / 4.8 steps/s so the onset frame lands exactly at t = 55.4; it keeps running to 57.0 (the road exits). The counter races in amber and freezes cream on the onset frame. Bottom third: a Pillow bar chart of the REAL 4x4 onset histogram (`exhaustive.json` -> `results.k4.histogram_log_bins`, log-x, 30 bars in cream), with an amber marker line at {LONGEST_ONSET} labelled `longest` and a secondary marker at {ONSET_STEP} labelled `empty grid`. | Auto-fit rule on the run's modified-cell bbox (section 2.5), 60 % contrast cap. Chart area x 100–940, y 1240–1560. | Card A 50.0–53.5: `The stubbornest start we found:` (Regular 52), plus the caption `{LONGEST_SOURCE}` (Mono 44, secondary, e.g. `seed 4491 · 64x64 · p=0.75`). If `adversarial` data exists in movie_facts, Card A instead reads `I evolved starts to stall it.` (Regular 56) — the only first-person line. Card B 53.5–57.0: `Longest delay: {LONGEST_ONSET_FMT} steps.` (Regular 56); at 55.4 `Still a road.` (Bold 84) snaps in beneath it. Chart title `onset step, all 65,536 4x4 starts` (Mono 36, secondary). | Band top y = 250. Counter y = 1180 (just above the chart), x = 100. | The longest crackle stretch in the piece (this run's real turn stream, −16 dBFS), pad cluster with rising cutoff and a minor-second rub (A2 + Bb2); a dry 2 kHz clock tick every 0.5 s. On the onset frame: crackle -> 220 Hz tone, sub thump, pad resolves to A major: the same resolution as S07, now as a punchline. |
| **S13 VERDICT** | 57.0–62.0 | HARD CUT to plain `#0B0D12`; the S08 road frame at 15 % opacity behind. Three mono lines snap in at 57.0, 57.4, 57.8; body line at 59.5. | n/a | `{TOTAL_TESTED_FMT} starts tested.` / `{TOTAL_TESTED_FMT} highways.` / `0 exceptions.` (Mono 64, cream; the `0` in amber). Then `That's evidence.` / `Not a proof.` (Bold 72, "Not a proof." amber). **Honesty rule:** if any run hit the step cap, line 3 becomes `{CAP_HITS} still unresolved.` in red and line 2 shows the certified count. | Lines left-aligned at x = 100, y = 520, 620, 720. Body lines at y = 1000, 1090. | Three dry filtered thuds for the three lines. The pad stops entirely on "Not a proof." (59.5); only the naked 220 Hz turn-stream tone remains at −22 dBFS. |
| **S14 SCORECARD** | 62.0–68.0 | Background: the empty-grid highway continuing at 300 steps/s, follow-cam, 8 px/cell, at 25 % opacity. Three lines stack in at 62.0, 64.0, 66.0 and stay to 68.0; line 3 gets a slow pulsing amber underline. | Follow-cam on the ant, 135 cells across. | Line 1: pill `PROVEN` + `It never gets trapped.` (Regular 56) + `Bunimovich & Troubetzkoy 1992` (Mono 40). Line 2: pill `PROVEN` + `It can run any logic circuit.` + `Gajardo, Moreira & Goles 2002`. Line 3: pill `UNPROVEN` (amber) + `It always builds the road.` + `every finite start, tested: yes` (Mono 40). | Pills at x = 100; lines at y = 420, 760, 1100 (pill above the sentence, citation beneath, each block ~240 px tall). | Tone quietly under lines 1 and 2, a bell (A4) on each PROVEN pill; on line 3 the tone drops out and only the drone remains, so silence marks the open problem. |
| **S15 CTA** | 68.0–74.0 | HARD CUT: the empty-grid run re-seeks to {ONSET_STEP}−1,500 and replays the hook shot (road erupts at 68.5 and streaks to the lower-left) so the last frame mirrors the first. 73.5–74.0 fade to `#0B0D12`. | Identical to S01. | `Can YOU find a start` / `that never` / `builds a road?` (Bold 72, three lines, fade in at 68.2). Below: `Any finite start counts.` / `Proof or counterexample?` / `Argue in the comments.` (Regular 48). Credit block: `made by Claude (an AI)` (Mono 40) / `github: evanmack45/langtons-ant-highway` (Mono 36). | Question band top y = 300. Sub-lines band y = 640–830. Credit band top y = 1380 (two lines, ends ~1490). | Crackle -> tone on the onset frame as in S01, full A major pad, then from 72.0 the tone is crossfaded into the per-step plucks as the displayed speed decelerates 3,000 -> 8 -> 2 steps/s (72.0–73.5): an audible slowing tick-tock of the highway's real R/L pattern. Final sound at 73.5: one low L pluck (A3) decaying into silence at 74.0. |

### 3.3 Mosaic tile table ({MOSAIC_TILES}, real 4x4 configs from `research/exhaustive/out/k4_records.csv`)

| tile (row, col) | start delay | cfg index | black cells (x, y) | onset s | certified at | direction |
|---|---|---|---|---|---|---|
| (1,1) | 0.0 s | 45206 | (−1,−2) (0,−2) (−2,−1) (1,−1) (−2,1) (−1,1) (1,1) | 19,039 | 22,022 | −x,−y |
| (1,2) | 0.4 s | 31091 | (−2,−2) (−1,−2) (−2,−1) (−1,−1) (0,−1) (−2,0) (1,0) (−2,1) (−1,1) (0,1) | 14,014 | 16,198 | −x,+y |
| (2,1) | 0.8 s | 21144 | (1,−2) (−2,−1) (1,−1) (−1,0) (−2,1) (0,1) | 9,002 | 11,186 | +x,−y |
| (2,2) | 1.2 s | 8636 | (0,−2) (1,−2) (−2,−1) (−1,−1) (1,−1) (−2,0) (−1,1) | 4,002 | 6,186 | +x,+y |
| (3,1) | 1.6 s | 6362 | (−1,−2) (1,−2) (−2,−1) (0,−1) (1,−1) (1,0) (−2,1) | 2,501 | ~4,700 | −x,−y |
| (3,2) | 2.0 s | 6077 | (−2,−2) (0,−2) (1,−2) (−2,−1) (−1,−1) (1,−1) (−2,0) (−1,0) (0,0) (−2,1) | 1,000 | ~3,200 | +x,+y |

At 6,000 steps/s the certification moments fall at ≈ 40.2, 40.4, 40.5, 40.7, 41.1, 41.7 s (ascending),
all inside the 38–44 window with >= 2 s of visible road afterwards. The renderer re-derives each
tile's onset with `core.find_onset` and draws the label from that value (it must equal the CSV).

---

## 4. Audio design (numpy, 48 kHz stereo, muted viewing never required)

Master: sum of layers -> soft limiter -> normalize so integrated loudness ≈ −14 LUFS
(verify with `ffmpeg -i final.mp4 -af ebur128 -f null -`) and true peak <= −1 dBTP. Any hit is
placed with `core.place`; envelopes with `core.adsr`; filters with `core.lowpass`.

### 4.1 Layer 1 — the turn-stream oscillator (the instrument; sonifies the ant's own turns)

- For each run, build `w[k] = +1 if t[k] == 'R' else −1` (k = step index, from the simulation's turn array).
- A **read head** moves through `w` at a constant **22,880 turns/s**, so a 104-periodic stretch is exactly
  **220 Hz (A3)**; a second head at 11,440 turns/s (110 Hz, A2) is mixed at −9 dB for body. Render both
  at 192 kHz sample-and-hold, `lowpass` at 6 kHz, decimate by 4 to 48 kHz.
- **Sync to the picture:** each frame f has a displayed step S_f. If head index H < S_f, or
  H − S_f > 1,600 + j (j uniform in [0, 800], seeded), jump H -> S_f + ((H − S_f) mod 104) with a
  6 ms equal-power crossfade. In the periodic regime the jump is a multiple of 104, so the tone is
  phase-continuous by construction; in chaos the data is noise anyway. The sound at time t is therefore
  always "the ant's next ~1,600 turns from the step you are looking at" — honest sonification.
- Chaotic data = dense crackle; periodic data = a steady tone whose timbre IS the highway's R/L pattern.
  The change happens on the onset frame, exactly when the amber ribbon starts.
- Levels: −20 -> −16 dBFS across S05, −14 dBFS in S07/S08, −26 dBFS per mosaic tile, −22 dBFS in S13,
  muted during S06 silence, S09, S11.

### 4.2 Layer 2 — step plucks (below 20 steps/s)

- R = E4 329.6 Hz, L = A3 220 Hz: decaying sine + 2nd (−6 dB) + 3rd (−12 dB) harmonics, `adsr(a=3 ms,
  d=120 ms, s=0.3, r=230 ms)`, 350 ms total, plus a 3 ms band-passed click at the flip instant.
- Used in S02–S03 (one per step), S04 until 20 steps/s (then 0.5 s crossfade to Layer 1), and S15's
  deceleration (72.0–73.5), ending on a single L pluck.

### 4.3 Layer 3 — drone and pad

- Drone: sines at 55 and 110 Hz with ±3 cent slow detune (0.1 Hz LFO), −24 dBFS, present from 0.0
  to 73.0 except the S06 silence. Adds E (82.4 Hz) at S04.
- Pad (`pad_chord`, 4 detuned voices, lowpass): chaos = A2 + Bb3 + E4 + F4, cutoff 400 -> 2,500 Hz,
  +8 cent drift (S05, S12 before onset); highway = A2, E3, A3, C#4, E4, cutoff 1,200 Hz (S07, S08,
  S11 completion, S12 after onset, S15); thin to a lone A2 on "Nobody can prove it always will" (S10 B)
  and S09; A2 + Bb2 rub in S12; pad OFF on "Not a proof." (S13) and on UNPROVEN (S14 line 3).

### 4.4 Layer 4 — hits and punctuation

| Moment | Sound |
|---|---|
| Onset frames (S01 0.5, S07 20.0, S12 55.4, S15 68.5) | 48 Hz sub thump, 250 ms exponential decay, −8 dBFS |
| S06 16.0 | 0.4 s hard silence, then one 48 Hz thump with a 2 s tail |
| S07 | kick (48 Hz, 120 ms) once per second on the frame boundary |
| S08 | white-noise riser band-pass 200 Hz -> 8 kHz over 3 s; bell A4 (880 Hz, 2 s decay) on PROVEN |
| S09 | click clusters per re-roll; 150 Hz wooden knock on lock |
| S10 | pentatonic blips A4 B4 C#5 E5 F#5 A5 (short sines, 300 ms) in certification order, unresolved |
| S11 | micro-ticks (1 per dot, capped 200/s) -> filtered noise shimmer; A-major chord hit at 47.5; slot clicks on side bars |
| S12 | dry 2 kHz clock tick every 0.5 s until onset |
| S13 | three filtered thuds (120 Hz, 80 ms) on the three lines |
| S14 | bell A4 on each PROVEN pill; nothing on UNPROVEN |
| S15 | tone -> slowing plucks -> single L pluck -> silence at 74.0 |

### 4.5 Muted fallback

Every audio event has a visual twin: onset = amber ribbon + counter turning cream + frozen barcode;
PROVEN bell = green pill; "Not a proof." = amber text; the loop = age-tint glow. The video is
fully understandable with sound off; sound on adds "noise becomes a note made of the ant's own turns".

---

## 5. Data pipeline (what the renderer reads; never fakes)

- `research/results/movie_facts.json` (section 6) is the only source of on-screen numbers.
- The empty-grid run is simulated inside the renderer (`core.simulate(60000, (), size=2048)`) and its
  onset must equal `onset_step_empty_grid` (assert; abort otherwise).
- Mosaic tiles are simulated inside the renderer from the black-cell lists in 3.3; each onset is
  re-derived with `core.find_onset` and asserted against `k4_records.csv`.
- The dot wall reads `research/exhaustive/out/k4_records.csv` (`status` column: 0 = certified) so a
  non-certified pattern would really show red.
- The histogram reads `research/results/exhaustive.json -> results.k4.histogram_log_bins`.
- The longest-delay run is re-simulated inside the renderer from `{LONGEST_CONFIG}` and its onset
  must equal `{LONGEST_ONSET}` (assert).

---

## 6. Placeholder table

All fields live in `research/results/movie_facts.json` (produced by the research analysis step).
"Expected" values are what the repo's current results show at storyboard time (2026-09-19).

| Placeholder | movie_facts.json field | Expected | Formatting / rule |
|---|---|---|---|
| `{ONSET_STEP}` | `onset_step_empty_grid` | 9977 | raw integer for scheduling |
| `{ONSET_STEP_FMT}` | `onset_step_empty_grid` | "9,977" | thousands separators |
| `{PERIOD}` | `period` | 104 | must be 104, else abort |
| `{DISPLACEMENT}` | `displacement_per_period` | [−2, −2] | used to compute cells/s = steps/s × 2/104 |
| `{HIGHWAY_DIR}` | `direction_empty_grid` | "−x,−y" | maps to the lower-left corner on screen (y North = up); camera centers in S01/S07/S08/S15 are derived from the sign of the displacement, not hard-coded |
| `{N4}`, `{N4_HIGHWAY}` | `exhaustive["4"].n_configs`, `.n_highway` | 65,536 / 65,536 | if `n_highway < n_configs`, S11 card B reads `{N4_HIGHWAY} / {N4} certified` and the missing patterns are red dots |
| `{N3}`, `{N3_HIGHWAY}` | `exhaustive["3"].n_configs`, `.n_highway` | 512 / 512 | side bar |
| `{N5}`, `{N5_HIGHWAY}` | `exhaustive["5"].n_configs`, `.n_highway` | not merged yet (k5 still running at storyboard time) | side bar shown ONLY if the key `"5"` exists AND `n_highway == n_configs == 33,554,432` AND cap hits == 0; otherwise omitted entirely (never show a partial count) |
| `{MAX_ONSET_4}` | `exhaustive["4"].max_onset` | 119,673 | candidate for LONGEST_ONSET |
| `{N_RANDOM}`, `{N_RANDOM_HIGHWAY}` | `random.total_tested`, `random.total_highway` | 400,000 / 400,000 | side bar; if unequal, show both numbers as they are |
| `{RANDOM_LONGEST}` | `random.longest_onset` | 196,974 | candidate for LONGEST_ONSET |
| `{ADV_LONGEST}`, `{CAP_HITS}` | `adversarial.longest_onset`, `adversarial.cap_hits` | absent (no adversarial run exists at storyboard time) | if the `adversarial` object is absent, S12 uses the "stubbornest start" wording; if present, S12 card A uses the first-person line and `{CAP_HITS} > 0` triggers the S13 honesty rule |
| `{LONGEST_ONSET}` / `{LONGEST_ONSET_FMT}` | max of `exhaustive[k].max_onset`, `random.longest_onset`, `adversarial.longest_onset` | 196,974 | |
| `{LONGEST_CONFIG}` | the black-cell list of that run: `random.longest_config.black_cells` (or `exhaustive["4"].max_onset_config.black_cells`, or `adversarial.longest_config.black_cells`) | random sample k=64, p=0.75, seed 20260919, index 4491 (3,121 black cells; regenerate with `research/random/randexp dump 64 0.75 20260919 4491`) | movie_facts MUST carry the cell list (or the k/p/seed/index tuple) for the winning source; the renderer aborts if it cannot reproduce `{LONGEST_ONSET}` |
| `{LONGEST_SOURCE}` | derived from the same object | "seed 4491 · 64x64 · p=0.75" | Mono 44 caption in S12 |
| `{TOTAL_TESTED}` / `{TOTAL_TESTED_FMT}` | sum of `exhaustive[k].n_configs` over merged k + `random.total_tested` + (adversarial count if present) | 466,066 (= 2 + 16 + 512 + 65,536 + 400,000) | S13 line 1; line 2 uses the sum of the `n_highway` fields; line 3 = tested − highway, expected 0 |
| `{TILE_ONSET_i}` | re-derived in-render from the six configs in 3.3 | 19,039 / 14,014 / 9,002 / 4,002 / 2,501 / 1,000 | must match `k4_records.csv` |
| `{MOSAIC_TILES}` | table 3.3 (static in this storyboard, sourced from `k4_records.csv`) | | |

Missing required field => the renderer aborts with the field name; it never substitutes a number.

---

## 7. Acceptance checklist (reviewers)

**File specs**
- [ ] 1080 x 1920, 30.000 fps, exactly 2220 frames (2370 with the optional walls insert), H.264, `yuv420p`, AAC 192 kbit/s, stereo 48 kHz; `ffprobe` confirms; file <= 50 MB (target CRF 20–23; re-encode if larger).
- [ ] Audio integrated loudness within −16..−12 LUFS, true peak <= −1 dBTP (`ffmpeg -af ebur128`).

**Legibility and safe zone**
- [ ] Every drawn string measured <= 880 px at its final size (renderer log shows zero shrinks, or lists them).
- [ ] Every text element, pill, chart, counter and tile border inside x 80..960, y 240..1600 (overlay pass: render frames 15, 90, 200, 300, 480, 540, 660, 750, 900, 1020, 1200, 1350, 1500, 1620, 1710, 1800, 1920, 2100, 2160 with the safe-zone rectangle drawn and inspect each).
- [ ] Body >= 48 px, mono captions >= 36 px, hero lines >= 72 px. Max 8 words per line.
- [ ] Every card >= 2.0 s at full opacity; no card shorter (S02, S03, S09 A are exactly 2.5 / 2.5 / 2.5).
- [ ] All text on a band or plain background; cream text over cream cells never occurs.

**Timing**
- [ ] Frame 15 (0.5 s) is the empty-grid onset frame; frame 480 (16.0 s) shows the counter at exactly {ONSET_STEP_FMT}; frame 600 (20.0 s) resumes; S07 advances exactly 104 steps per frame (turn-strip barcode is pixel-identical across frames 600–809).
- [ ] S12 onset frame at 55.4 s coincides with "Still a road." snapping in and the crackle -> tone change.
- [ ] S15 frames 2040–2100 mirror S01 frames 0–60 (same camera, same run); the loop back to frame 0 is clean.
- [ ] Audio events (thumps, bells, blips) land on the listed frames within ±1 frame.

**Science honesty**
- [ ] On-screen numbers equal the `movie_facts.json` fields (spot-check S06, S11, S12, S13 against the JSON).
- [ ] No 5x5 line unless the 5x5 result is merged and complete; no partial counts anywhere.
- [ ] If any run hit the step cap: red dots, "certified" wording in S11, the S13 honesty line; never round up.
- [ ] Theorem wording exactly: "No finite start can trap the ant." / "It never gets trapped." (1992) and "It can run any logic circuit." (2002). No "compute anything a computer can", no "no memory", no "never stops, ever".
- [ ] "It never turns back." (S08 A) is separated from the PROVEN pill (S08 B) and refers to this run; the OPEN/UNPROVEN and CTA lines both say "finite".
- [ ] Age-tint thresholds (1,040 steps) identical in every run shown; the highway is never special-cased.
- [ ] The mosaic, dot wall, histogram and longest run are driven from the repo's result files (section 5), not synthetic data.
- [ ] Video description text (for the upload) states: white cells are drawn dark; onset definition (CONVENTIONS.md); 5,000,000-step cap (exhaustive) / 20,000,000 (random); certification = 20 periods + 20-cell escape margin; precise citations: Bunimovich & Troubetzkoy 1992 (unboundedness); Gajardo, Moreira & Goles 2002 (simulation of any boolean circuit; P-hardness).

**Motion / rendering**
- [ ] No moiré at 1 px/cell (BOX downsample), road never thinner than 2 px, 60 % contrast cap active whenever > 100 steps/frame.
- [ ] Hard cuts only at the listed shot boundaries; all other camera changes eased.

---

## 8. Judge flaws fixed (traceability)

| Flaw (judges) | Fix |
|---|---|
| Four-line number wall at 48–52 s | S11 card B is one line; the rest are three small mono side bars; 5x5 line conditional |
| Five separate evidence set pieces 33–63 s | Walls beat removed from the main cut (Appendix A, only with data); evolution beat replaced by one live "stubbornest start" run + the real histogram; middle is now mystery -> mosaic -> count -> stubbornest -> verdict |
| 104 ticks/s groove buzzes on phones; 52/s breaks the bracket | Groove replaced by the turn-stream oscillator (220 Hz tone from the real turn string); the visual period device is the frozen barcode at 104 steps/frame plus the age-tint ribbon, independent of tick rate |
| 5x5 line assumes unmerged data | Conditional rule in section 6; omitted by default |
| 20,000 steps/s pull-back, six sims, R-fraction noise = tuning cost | S08 stays at 3,120 steps/s with a closed-form camera rule; mosaic tiles are six ordinary `simulate` calls; the oscillator replaces the R-fraction band-pass |
| Evolution beat inconsistent (119k+ steps in 18k) | Live run rate = LONGEST_ONSET / 4.8 s with auto-fit zoom-out |
| Hero 104 px line and the 44 px repo line overflow | Measured table 2.4; "Then THIS happens." at 76 px (856 px), credit at 38 px mono (823 px) |
| Sim grid too small for the road | size = 2048 for the empty-grid run, 4096+ for the longest run, asserted |
| Obstacle beat depends on unrun experiment | Appendix A only |
| "no memory", "compute anything a computer can", "It never stops. Ever." next to PROVEN, "Every single one", missing "finite" | "no randomness. no lookahead."; "It can run any logic circuit."; "It never turns back." separated from the PROVEN pill; "Every one we tried builds a road."; "finite" in S08 B, S09 B, S14 line 3, S15 |
| Ambiguous "Nobody knows why this happens" | Hook uses "2 rules. / Then THIS happens."; the mystery card reads "Nobody can prove why." and is backed by the UNPROVEN line |
| Camera direction assumed upper-right | All camera centers derived from `direction_empty_grid` (−x,−y = lower-left) |
| Random 64x64 tiles cannot certify in 1.5 s | Mosaic uses six pre-selected 4x4 configs with known onsets (table 3.3) |
| Photosensitivity at 300 steps/frame | 60 % contrast cap |

---

## Appendix A — optional WALLS insert (only if `movie_facts.json` contains `obstacle.n_tested` and `obstacle.n_rebuilt`)

Insert 5.0 s between S12 and S13 (S13 onward shifts by +5.0 s; total 79.0 s, 2370 frames).

| t | simulation | camera | text | audio |
|---|---|---|---|---|
| +0.0–+1.0 | Empty-grid run at step {ONSET_STEP}+3,120, 800 steps/s, follow-cam 10 px/cell | locked on ant | Card A (+0.0–+2.5): `A wall in its path?` (Regular 56) | tone running |
| +1.0 | A solid 12x12 block of marked cells (cream, amber outline) drops onto the road 40 cells ahead of the ant (2-frame screen shake). Block geometry = `obstacle.geometry` from movie_facts. | | | thump |
| +1.6–+3.6 | Ant hits the block; speed ramps to 6,000 steps/s; a new blob boils around the block; the renderer re-derives the new onset with `find_onset` and only then draws the new road as certified | pull back to show old road, block, blob, new road | Card B (+2.5–+5.0): `A mess... then a new road.` if the in-render run certifies within 5,000,000 steps and `obstacle.n_rebuilt == obstacle.n_tested`; otherwise `So far: always a new road.` (Regular 56) | tone -> crackle on impact; tone returns (an octave up, 440 Hz) on the new onset frame |

---

## Appendix B — one-paragraph video description (for the upload; keeps the on-screen claims auditable)

Langton's Ant: on an empty cell turn right, mark it, step; on a marked cell turn left, erase it, step
(white cells are drawn dark here; the rule is unchanged). From the empty grid the turn sequence becomes
104-periodic after step 9,977 (definition in research/CONVENTIONS.md) and the ant travels (−2,−2) cells
per period forever, certified by 20 exact periods plus a 20-cell escape margin. We tested every start in
a 1x1, 2x2, 3x3 and 4x4 box (65,536 patterns; step cap 5,000,000) and 400,000 random starts up to 64x64
(cap 20,000,000): all built a highway; longest delay 196,974 steps. Proven: no finite start can trap
the ant (Bunimovich & Troubetzkoy 1992); the ant can simulate any boolean circuit (Gajardo, Moreira &
Goles 2002). Open: does every finite start build the highway? Code and data:
github.com/evanmack45/langtons-ant-highway. Made by Claude (an AI).
