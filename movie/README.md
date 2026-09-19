# movie/ — renderer for "Two Rules, One Road"

A 79.0 s (2370-frame) 1080x1920 social-media video about Langton's Ant and the
highway conjecture, rendered frame by frame with numpy + Pillow and encoded with
ffmpeg (libx264 + aac).  The spec is `STORYBOARD.md` (74.0 s) plus its Appendix A
WALLS insert (5.0 s, director's cut); every deviation from it is listed in
`DEVIATIONS.md`, the upload text is `DESCRIPTION.md`.  Every headline number on screen
comes from the facts JSON passed on the command line; the onset histogram is read from
`research/results/exhaustive.json`, and the six mosaic patterns and the wall example are fixed
records that the renderer re-simulates and asserts against their recorded onsets.

## How to render

Run everything from this directory with `PYTHONPATH=$PWD` (the `movie/` directory)
(Python 3.11, numpy, Pillow, imageio-ffmpeg).

```bash
cd movie
export PYTHONPATH=$PWD
FACTS=../research/results/movie_facts.json          # verified facts (section 6 of the storyboard)
# The dot wall and the mosaic assertions read the committed research/results/exhaustive_k4_records.npz
# (packed from research/exhaustive/out/k4_records.csv, see "k4 records" below); a fresh clone renders as is.
# FACTS=build/movie_facts.provisional.json          # or: python3 facts_provisional.py  (marked provisional; it carries no
#   adversarial.obstacle_attack, so the WALLS insert aborts by field name with it - use the verified file)

# 1. picture (silent H.264) + per-frame audio timeline
python3 render.py --facts $FACTS --out build/langtons_ant_silent.mp4 --timeline build/timeline_full.json

# 2. sound (48 kHz stereo WAV, -14 LUFS, <= -3.5 dBTP) and the final muxed file
python3 audio.py --timeline build/timeline_full.json --wav build/langtons_ant.wav \
                 --mux build/langtons_ant_silent.mp4 --out langtons_ant.mp4

# 3. checks (the imageio-ffmpeg bundle ships ffmpeg only, no ffprobe, and neither is on PATH)
FF=$(python3 -c 'import core; print(core.ffmpeg_exe())')
$FF -hide_banner -i langtons_ant.mp4 2>&1 | grep -E 'Duration|Stream'        # streams, codecs, duration (bare `ffmpeg -i` exits non-zero: no output file)
$FF -hide_banner -nostats -i langtons_ant.mp4 -map 0:v -f null - 2>&1 | tail -2   # frame count
$FF -hide_banner -nostats -i langtons_ant.mp4 -af ebur128=peak=true -f null -     # integrated LUFS + true peak
```

(`audio.py --mux` prints the same probe.  If an `ffprobe` exists - `core.ffprobe_exe()` looks next to the bundled ffmpeg and on PATH -
`$(python3 -c 'import core; print(core.ffprobe_exe())') -v error -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames,pix_fmt,sample_rate,channels langtons_ant.mp4` works too.)

Development options of `render.py`:

| flag | effect |
|---|---|
| `--shots S07,S08` | render only those shots (audio events of unrendered frames are dropped, so `audio.py` stays aligned with the clip) |
| `--frames a:b` | absolute frame range (b exclusive); any start frame gives the same picture as a full render |
| `--preview` | 540x960 output with a fast x264 preset (the picture is rendered at full size, then downscaled) |
| `--dump-frames DIR` | also write every rendered frame as a PNG |
| `--safe-zone` | overlay the text safe zone (x 80..960, y 240..1600) |
| `--crf N` | x264 quality (default 21; the full film is 8.6 MB, -14.1 LUFS / -3.2 dBTP after `audio.py`) |

Example: `python3 render.py --facts $FACTS --out build/S07.mp4 --shots S07 --preview --dump-frames build/frames_S07 --safe-zone`.

`audio.py` options: `--target-lufs` (default -14), `--ceiling` (true-peak ceiling of the WAV in
dBTP, default -3.5 so the AAC encode, which overshoots by ~1-1.5 dB, stays under -1 dBTP), `--facts` (override the path stored in the timeline).

Scratch output goes to `build/` (gitignored): text-shrink logs next to each timeline
(`build/timeline_full_shrinks.log` for the full film; a partial render writes its own), memoised
simulations (`build/runs/*.npz`), timelines, previews, checklist frames (`build/check/`).

## k4 records (`research/results/exhaustive_k4_records.npz`)

The per-config results of the 4x4 sweep (`research/exhaustive/out/k4_records.csv`, 7 MB, gitignored
derived data written by `research/exhaustive/exhaust`) are committed in packed form so a fresh clone
renders without regenerating the CSV.  `make_k4_records_npz.py` writes the npz from the CSV
(`PYTHONPATH=. python3 make_k4_records_npz.py`); `common.load_k4_records` prefers the npz and falls
back to the CSV.  Arrays are indexed by config index 0..65535 (the bit encoding of `exhaustive.json`):

| array | dtype | meaning |
|---|---|---|
| `onset` | uint32 | the onset step `s` of that configuration |
| `status` | uint8 | the CSV `status` column, 0 = certified highway |
| `direction` | int8 | highway direction code, bit 0 = +x, bit 1 = +y: 0 `-x,-y`, 1 `+x,-y`, 2 `-x,+y`, 3 `+x,+y`; -1 when not certified |
| `source` | str | the CSV path the arrays were packed from |

The S11 dot wall reads `status` (a non-zero entry really draws red); each S10 mosaic tile's re-derived
onset is asserted against `onset[cfg]` and `status[cfg] == 0`.  If the CSV is regenerated, re-run the
packer (the exhaustive sweep is deterministic, so the arrays do not change).

## Module layout

| file | role |
|---|---|
| `core.py` | primitives: `simulate` / `GridPlayer` / `find_onset`, `Camera` / `render_grid` / `draw_ant`, fonts, `VideoWriter`, `mux_audio`, audio synth helpers (`adsr`, `place`, `lowpass`, ...) |
| `common.py` | shared layer: facts loading + validation and the derived placeholders (section 6), the exact splitmix64 regeneration of a random config, `RunCache` (empty grid, the stubborn 5x5 run, the walls run, the longest-anywhere run, six mosaic tiles; onsets asserted), the WALLS placement record + step schedule, `AgePlayer` (grid + `last_flip` age array), `render_run` (amber/cream age tint, visited tint, trail, hairline grid, 60 % contrast cap, BOX supersampling), the frame-exact step schedule (3.1), text/UI helpers (bands, fit-or-shrink, pills, counters, turn strip, histogram, dot wall), camera helpers, `LagSmoother`, `audio_state` |
| `render.py` | CLI + frame loop: shot table (3.2), `Ctx` handed to every scene, timeline JSON writer |
| `scenes_road.py` | S01–S08 and S15 (hook, rules demo, chaos, freeze, road, infinity, CTA) + `road_backdrop` |
| `scenes_evidence.py` | S09–S14 and WALLS (mystery box, mosaic, dot wall, stubbornest 5x5 start + histogram, the walls insert, verdict, scorecard) |
| `make_k4_records_npz.py` | packs the 4x4 per-config CSV into the committed npz (see "k4 records") |
| `audio.py` | section-4 sound engine driven only by the timeline: turn-stream oscillator (read heads re-synced to the displayed step), plucks, drone/pad, hits, noise shimmer, mute, soft limiter, ebur128-measured normalisation, true-peak limiter, mux + probe |
| `facts_provisional.py` | assembles `build/movie_facts.provisional.json` from `research/results/*.json` (marked `"provisional": true`) until the verified `movie_facts.json` exists |
| `SCENES_CONTRACT.md` | what a scene function must return and what `ctx` provides |
| `STORYBOARD.md`, `DEVIATIONS.md`, `DESCRIPTION.md` | the spec, the list of departures from it, the upload description |

## Timeline (director's cut)

| shot | t (s) | frames | | shot | t (s) | frames |
|---|---|---|---|---|---|---|
| S01 hook | 0.0–2.0 | 0–59 | | S09 mystery | 33.0–38.0 | 990–1139 |
| S02 rule 1 | 2.0–4.5 | 60–134 | | S10 mosaic | 38.0–44.0 | 1140–1319 |
| S03 rule 2 | 4.5–7.0 | 135–209 | | S11 count | 44.0–50.0 | 1320–1499 |
| S04 whole program | 7.0–10.0 | 210–299 | | S12 stubbornest 5x5 start | 50.0–57.0 | 1500–1709 |
| S05 chaos | 10.0–16.0 | 300–479 | | WALLS (Appendix A) | 57.0–62.0 | 1710–1859 |
| S06 freeze | 16.0–20.0 | 480–599 | | S13 verdict | 62.0–67.0 | 1860–2009 |
| S07 the road | 20.0–27.0 | 600–809 | | S14 scorecard | 67.0–73.0 | 2010–2189 |
| S08 to infinity | 27.0–33.0 | 810–989 | | S15 CTA | 73.0–79.0 | 2190–2369 |

Onset frames: S01 15 (0.5 s), S06 480, S07 600, S12 1662 (55.4 s), WALLS impact 1740 (58.0 s) and
rebuilt-road onset 1789 (59.63 s), S15 2205 (73.5 s).  S01/S15 hook framing: 130 cells across, blob centre at
screen (590, 1090); S15 bands: question 280-626, sub-lines 650-903 (24 px gap), credit 1437-1600 (bottom-aligned to the safe zone).

Scene functions have the signature `S07(ctx, t_local, frame) -> (PIL.Image 1080x1920, audio_state, events)`
and are pure per frame; `audio.py` never looks at pixels, only at the timeline that `render.py` writes.

## Facts contract (`--facts`)

The renderer aborts, naming the field, when a required field is missing; it never substitutes a
number.  The verified `research/results/movie_facts.json` uses its own layout; `common.adapt_verified_schema`
maps it onto the section-6 names below before validation (`exhaustive.kN` -> `N`, `n_cap` -> `cap_hits`,
`exhaustive.4.histogram_log_bins` + `k4_records_csv` read from the result file named by `exhaustive.source`,
`random.longest_config` parsed from `random.longest_config_summary` as the `(k, p, seed, index, n_black)`
tuple, `random.max_k` from the sweep tables, `adversarial.n_tested` <- `total_runs`).  When present,
`total_runs_all_experiments` / `total_runs_non_certified` must equal the section-6 sums (abort otherwise).
Fields (STORYBOARD section 6):

| field | required | use |
|---|---|---|
| `onset_step_empty_grid` (int) | yes | `{ONSET_STEP}`; the in-render empty-grid simulation must reproduce it (asserted) |
| `period` (int) | yes, must be 104 | `{PERIOD}` |
| `displacement_per_period` `[dx, dy]` | yes | cells per period; its signs drive every camera centre (`highway_sign`) |
| `direction_empty_grid` (e.g. `"-x,-y"`) | yes, must agree with the displacement | `{HIGHWAY_DIR}` |
| `exhaustive.<k>.{n_configs, n_highway, max_onset, cap_hits}` | `"4"` and `"5"` required; `"1".."5"` as merged | S11 counts / side bars, S13 totals; include a `k` only when its sweep is complete |
| `exhaustive.4.histogram_log_bins` `[{lo, hi, count}, ...]` | yes (read from `exhaustive.source`) | kept for the section-6 contract |
| `exhaustive.5.histogram_log_bins` | yes (read from `exhaustive.source`) | S12 histogram (`onset step, all 33,554,432 5x5 starts`) |
| `exhaustive.5.max_onset_config.{black_cells, n_black}` + `exhaustive.5.max_onset`, `n_configs` | yes | S12 plays this run (the provable 5x5 maximum, 233,232); re-simulated and asserted; `n_configs` in the caption and the chart title. The sweep must be complete (`n_highway == n_configs`, `cap_hits == 0`), else abort |
| `exhaustive.<k>.max_onset_config.{cfg_index, black_cells}` | optional | candidate for `{LONGEST_CONFIG}` |
| `exhaustive.5` | see above | the 5x5 side bar is shown only when `n_highway == n_configs == 33,554,432` and `cap_hits == 0` |
| `random.{total_tested, total_highway, longest_onset}` | yes | side bar, S13 totals, `{RANDOM_LONGEST}` |
| `random.longest_config` | yes | `black_cells`, or the `(k, p, seed, index)` tuple (regenerated with the exact randexp splitmix64; `n_black` checked when present); its `k` is the box size of the S12 secondary line `(512x512 box)` |
| `random.max_k` (or `random.k_values`) | yes | the box size in the S11 side bar `random, up to KxK:` |
| `adversarial.{longest_onset, cap_hits, n_tested, longest_config}` (+ optional `n_highway`, `longest_config.box_k`) | optional | when present: the count joins `{TOTAL_TESTED}`, `cap_hits > 0` triggers the S13 honesty line |
| `adversarial.obstacle_attack.{placements, hits, hits_rebuilt_highway}` (mapped to `obstacle`) | yes (WALLS) | WALLS card B `616 hits. 616 new roads.` / `1,512 walls on or beside the road` (attack A placed 896 of the 1,512 beside the highway strip; only the 616 hits were in the ant's path) |
| `k4_records_csv` (path relative to the repo) | fallback | the per-config 4x4 records; the committed npz `research/results/exhaustive_k4_records.npz` is preferred (see "k4 records") |
| `mosaic_tiles` | optional | overrides the six STORYBOARD 3.3 tiles (`row, col, delay, cfg, cells, onset, dir`) |
| `provisional` (bool) | optional | printed at startup; the provisional file must not be used for the final upload |

Derived in `common.load_facts`: `LONGEST_ONSET` = max of `exhaustive[k].max_onset`,
`random.longest_onset`, `adversarial.longest_onset` (exact ties: exhaustive > random > adversarial),
its cell list, origin, box size (`longest_box_k`) and the `{LONGEST_SOURCE}` caption — shown on the S12
secondary line `longest anywhere: 1,323,594 steps (512x512 box)` and re-simulated to assert the onset;
the S12 run itself (`stubborn_*`: the provable 5x5 maximum), `TOTAL_TESTED` / `TOTAL_HIGHWAY` /
exceptions (counts of runs, hence the S13 wording `runs tested.`), `CAP_HITS`, and `show_k5`.

The WALLS insert's obstacle placement is not in the facts file: `common.WALLS_PLACEMENT` records ONE
real line of `research/adversarial/out/attack_a.jsonl` (shape 3x3, anchor (-108, -84), contact step
14,600, onset 18,043, extra chaos 3,443, new direction -x,+y); the renderer re-simulates the empty grid
plus those nine cells, re-derives the contact step and the onset and asserts both against the record,
and checks the record against the jsonl line whenever that (gitignored) file is present.

## What the verified render shows (facts of 2026-09-19)

`research/results/movie_facts.json`: onset 9,977 (S06); `I tested it 41,835,387 times.` (S10); 65,536 /
65,536 4x4 starts, 3x3 box 512 / 512, random up to 512x512 4,730,000 / 4,730,000, 5x5 box 33,554,432 /
33,554,432 (S11); the stubbornest 5x5 start, 11 cells, longest delay 233,232 steps, with the secondary
line `longest anywhere: 1,323,594 steps (512x512 box)` and the 5x5 onset histogram (S12); 616 hits /
616 new roads / 1,512 walls on or beside the road (WALLS); 41,835,387 runs tested / 41,835,387 highways / 0 exceptions (S13).

Upload description: `DESCRIPTION.md` (Appendix B of the storyboard with the verified numbers).

## Fonts

The renderer needs the DejaVu Sans, DejaVu Sans Mono (regular and bold) and Liberation Sans TTF
files. `core.find_font_file` searches the usual font directories on Linux, macOS and Windows,
`$LANGTON_FONT_DIR` (searched recursively), and matplotlib's bundled DejaVu copy if that package
is installed. On a machine without them, install `fonts-dejavu` / `dejavu-fonts` or point
`LANGTON_FONT_DIR` at a directory containing the files; a missing font raises a `FileNotFoundError`
naming the file and the directories searched.
