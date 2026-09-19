# movie/ — renderer for "Two Rules, One Road"

A 74.0 s (2220-frame) 1080x1920 social-media video about Langton's Ant and the
highway conjecture, rendered frame by frame with numpy + Pillow and encoded with
ffmpeg (libx264 + aac).  The spec is `STORYBOARD.md`; every deviation from it is
listed in `DEVIATIONS.md`.  Every number on screen comes from a facts JSON passed
on the command line — nothing is hard-coded.

## How to render

Run everything from this directory with `PYTHONPATH=/home/user/Claude-experiment/movie`
(Python 3.11, numpy, Pillow, imageio-ffmpeg).

```bash
cd /home/user/Claude-experiment/movie
export PYTHONPATH=$PWD
FACTS=../research/results/movie_facts.json          # verified facts (section 6 of the storyboard)
# The dot wall and the mosaic assertions read research/exhaustive/out/k4_records.csv, which is not
# committed (gitignored derived data).  On a fresh clone regenerate it once (a few seconds):
#   (cd ../research/exhaustive && gcc -O3 -march=native -o exhaust exhaust.c && mkdir -p out && ./exhaust 4 0 65536 5000000 out/k4 1)
# FACTS=build/movie_facts.provisional.json          # or: python3 facts_provisional.py  (marked provisional)

# 1. picture (silent H.264) + per-frame audio timeline
python3 render.py --facts $FACTS --out build/langtons_ant_silent.mp4 --timeline build/timeline_full.json

# 2. sound (48 kHz stereo WAV, -14 LUFS, <= -3.5 dBTP) and the final muxed file
python3 audio.py --timeline build/timeline_full.json --wav build/langtons_ant.wav \
                 --mux build/langtons_ant_silent.mp4 --out langtons_ant.mp4

# 3. checks (the imageio-ffmpeg bundle ships ffmpeg only, no ffprobe, and neither is on PATH)
FF=$(python3 -c 'import core; print(core.ffmpeg_exe())')
$FF -hide_banner -i langtons_ant.mp4                                         # streams, codecs, duration
$FF -hide_banner -nostats -i langtons_ant.mp4 -map 0:v -f null - 2>&1 | tail -2   # frame count
$FF -hide_banner -nostats -i langtons_ant.mp4 -af ebur128=peak=true -f null -     # integrated LUFS + true peak
```

(`audio.py --mux` prints the same probe.  If a system `ffprobe` exists, `ffprobe -v error -show_entries
stream=codec_name,width,height,r_frame_rate,nb_frames,pix_fmt,sample_rate,channels langtons_ant.mp4` works too.)

Development options of `render.py`:

| flag | effect |
|---|---|
| `--shots S07,S08` | render only those shots (audio events of unrendered frames are dropped, so `audio.py` stays aligned with the clip) |
| `--frames a:b` | absolute frame range (b exclusive); any start frame gives the same picture as a full render |
| `--preview` | 540x960 output with a fast x264 preset (the picture is rendered at full size, then downscaled) |
| `--dump-frames DIR` | also write every rendered frame as a PNG |
| `--safe-zone` | overlay the text safe zone (x 80..960, y 240..1600) |
| `--crf N` | x264 quality (default 21; the full film is ~12 MB) |

Example: `python3 render.py --facts $FACTS --out build/S07.mp4 --shots S07 --preview --dump-frames build/frames_S07 --safe-zone`.

`audio.py` options: `--target-lufs` (default -14), `--ceiling` (true-peak ceiling of the WAV in
dBTP, default -3.5 so the AAC encode, which overshoots by ~1-1.5 dB, stays under -1 dBTP), `--facts` (override the path stored in the timeline).

Scratch output goes to `build/` (gitignored): text-shrink logs next to each timeline
(`build/timeline_full_shrinks.log` for the full film; a partial render writes its own), memoised
simulations (`build/runs/*.npz`), timelines, previews, checklist frames (`build/check/`).

## Module layout

| file | role |
|---|---|
| `core.py` | primitives: `simulate` / `GridPlayer` / `find_onset`, `Camera` / `render_grid` / `draw_ant`, fonts, `VideoWriter`, `mux_audio`, audio synth helpers (`adsr`, `place`, `lowpass`, ...) |
| `common.py` | shared layer: facts loading + validation and the derived placeholders (section 6), the exact splitmix64 regeneration of a random config, `RunCache` (empty grid, longest-delay run, six mosaic tiles; onsets asserted), `AgePlayer` (grid + `last_flip` age array), `render_run` (amber/cream age tint, visited tint, trail, hairline grid, 60 % contrast cap, BOX supersampling), the frame-exact step schedule (3.1), text/UI helpers (bands, fit-or-shrink, pills, counters, turn strip, histogram, dot wall), camera helpers, `LagSmoother`, `audio_state` |
| `render.py` | CLI + frame loop: shot table (3.2), `Ctx` handed to every scene, timeline JSON writer |
| `scenes_road.py` | S01–S08 and S15 (hook, rules demo, chaos, freeze, road, infinity, CTA) + `road_backdrop` |
| `scenes_evidence.py` | S09–S14 (mystery box, mosaic, dot wall, stubbornest start + histogram, verdict, scorecard) |
| `audio.py` | section-4 sound engine driven only by the timeline: turn-stream oscillator (read heads re-synced to the displayed step), plucks, drone/pad, hits, noise shimmer, mute, soft limiter, ebur128-measured normalisation, true-peak limiter, mux + probe |
| `facts_provisional.py` | assembles `build/movie_facts.provisional.json` from `research/results/*.json` (marked `"provisional": true`) until the verified `movie_facts.json` exists |
| `SCENES_CONTRACT.md` | what a scene function must return and what `ctx` provides |
| `STORYBOARD.md`, `DEVIATIONS.md` | the spec and the list of departures from it |

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
| `exhaustive.<k>.{n_configs, n_highway, max_onset, cap_hits}` | `"4"` required; `"1".."5"` as merged | S11 counts / side bars, S13 totals; include a `k` only when its sweep is complete |
| `exhaustive.4.histogram_log_bins` `[{lo, hi, count}, ...]` | yes | S12 histogram |
| `exhaustive.<k>.max_onset_config.{cfg_index, black_cells}` | optional | candidate for `{LONGEST_CONFIG}` |
| `exhaustive.5` | optional | the 5x5 side bar is shown only when `n_highway == n_configs == 33,554,432` and `cap_hits == 0` |
| `random.{total_tested, total_highway, longest_onset}` | yes | side bar, S13 totals, `{RANDOM_LONGEST}` |
| `random.longest_config` | yes | `black_cells`, or the `(k, p, seed, index)` tuple (regenerated with the exact randexp splitmix64; `n_black` checked when present) |
| `random.max_k` (or `random.k_values`) | yes | the box size in the S11 side bar `random, up to KxK:` |
| `adversarial.{longest_onset, cap_hits, n_tested, longest_config}` (+ optional `n_highway`, `longest_config.box_k`) | optional | when present: S12 uses the first-person card, the count joins `{TOTAL_TESTED}`, `cap_hits > 0` triggers the S13 honesty line |
| `k4_records_csv` (path relative to the repo) | yes for S10/S11 | per-config `status` (0 = certified) for the dot wall; every mosaic tile's re-derived onset is asserted against its `s` and `status`. The file (`research/exhaustive/out/k4_records.csv`, 7 MB) is gitignored derived data: on a fresh clone regenerate it first (see "How to render") |
| `mosaic_tiles` | optional | overrides the six STORYBOARD 3.3 tiles (`row, col, delay, cfg, cells, onset, dir`) |
| `obstacle.{n_tested, n_rebuilt, geometry}` | optional | reserved for the Appendix A walls insert (not rendered) |
| `provisional` (bool) | optional | printed at startup; the provisional file must not be used for the final upload |

Derived in `common.load_facts`: `LONGEST_ONSET` = max of `exhaustive[k].max_onset`,
`random.longest_onset`, `adversarial.longest_onset` (exact ties: exhaustive > random > adversarial),
its cell list, origin and the `{LONGEST_SOURCE}` caption (S12 uses the first-person card only when the
origin is `adversarial`), `TOTAL_TESTED` / `TOTAL_HIGHWAY` / exceptions (counts of runs, hence the S13
wording `runs tested.`), `CAP_HITS`, and `show_k5`.  The longest-delay run is re-simulated and its
onset asserted.

## What the verified render shows (facts of 2026-09-19)

`research/results/movie_facts.json`: onset 9,977 (S06); 65,536 / 65,536 4x4 starts, 3x3 box 512 / 512,
random up to 512x512 4,730,000 / 4,730,000, 5x5 box 33,554,432 / 33,554,432 (S11); longest delay
1,323,594 steps for the random sample `index 9269 · 512x512 · p=0.5` (S12); 41,835,387 runs tested /
41,835,387 highways / 0 exceptions (S13).

Upload description (Appendix B of the storyboard, updated to the verified numbers): Langton's Ant: on an
empty cell turn right, mark it, step; on a marked cell turn left, erase it, step (white cells are drawn
dark here; the rule is unchanged). From the empty grid the turn sequence becomes 104-periodic after step
9,977 (definition in research/CONVENTIONS.md) and the ant travels (-2,-2) cells per period forever,
certified by 20 exact periods plus a 20-cell escape margin (for the 5x5 sweep the per-period displacement
was checked by sign only; 1x1-4x4 also checked the (+-2,+-2) magnitude). We ran every start in a 1x1,
2x2, 3x3, 4x4 and 5x5 box (33,620,498 runs, nested boxes counted once per box; step cap 5,000,000),
4,730,000 random starts in boxes up to 512x512 (cap 20,000,000) and 3,484,889 adversarial runs
(hill-climbed 12x12 patterns, structured seeds and obstacle placements; cap 50,000,000): 41,835,387 runs,
all built a highway; longest delay 1,323,594 steps (a random 512x512 start), longest for a start of at
most 16 cells 259,274 (four 2x2 obstacles), provable 5x5 maximum 233,232. Proven: no finite start can trap
the ant (Bunimovich & Troubetzkoy 1992); the ant can simulate any boolean circuit (Gajardo, Moreira & Goles
2002). Open: does every finite start build the highway? Code and data:
github.com/evanmack45/Claude-experiment. Made by Claude (an AI).
