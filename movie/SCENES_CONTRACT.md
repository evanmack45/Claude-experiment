# SCENES_CONTRACT — what a scene module must provide

Read this file, `common.py`, `core.py` and `STORYBOARD.md`. Nothing else is needed.
Run everything from `movie/` with `PYTHONPATH=/home/user/Claude-experiment/movie`.

## 1. File ownership

| File | Shots | Owner |
|---|---|---|
| `scenes_road.py` | `S01 S02 S03 S04 S05 S06 S07 S08 S15` + `road_backdrop(ctx, frame)` | road implementer |
| `scenes_evidence.py` | `S09 S10 S11 S12 WALLS S13 S14` | evidence implementer |
| `common.py`, `render.py`, `audio.py`, `core.py` | shared; do not edit (ask the architect; if a helper is missing, add a private helper inside your own module) | architect |

Both stub files already exist with every function present; replace the bodies, keep the names.
`DEVIATIONS.md`: append one line per deviation from the storyboard (`- Sxx: what / why`).

## 2. Scene function signature

```python
def S07(ctx, t_local: float, frame: int) -> tuple[PIL.Image.Image, dict, list]:
```

* `t_local` = seconds since the shot's first frame (`ctx.t` is the absolute time, `frame` the absolute frame index, `frame = round(t*30)`). The film is 79.0 s = 2370 frames (`common.N_FRAMES`): S01-S12 as in STORYBOARD 3.2, then `WALLS` 57.0-62.0 (Appendix A insert), `S13` 62.0-67.0, `S14` 67.0-73.0, `S15` 73.0-79.0 (`common.T_WALLS`, `T_S13`, `T_S14`, `T_S15`; the shifted scenes use `ctx.shot.t0` + local offsets, never absolute literals).
* Return a **1080 x 1920 RGB** `PIL.Image` (use `common.new_frame()` / `common.render_run()`), the per-frame **audio state** (`common.audio_state(...)`) and a **list of one-shot events** (may be empty).
* Scene functions must be pure in the render sense: the same `(frame)` always yields the same picture. Frames are rendered in ascending order but a partial render (`--frames a:b`) may start anywhere in a shot; keep any per-frame smoothing inside `ctx.lag` (see 3.4), which replays from the shot start.
* `road_backdrop(ctx, frame)` (scenes_road only) returns the grid-only picture of the empty-grid run as S08 draws it at `frame` — no cards, no counter. `ctx.road_backdrop(989)` caches it; S09 and S13 blend it behind their plain background.

## 3. What `ctx` provides (`render.Ctx`)

### 3.1 Data
* `ctx.facts` — `common.Facts`. **Every number on screen comes from here.** Fields: `onset`, `onset_fmt`, `period`, `displacement`, `direction`, `highway_sign` (sx, sy: -1,-1 = lower-left), `exhaustive["4"]["n_configs"|"n_highway"|"max_onset"|"cap_hits"]` (keys "1".."5" as merged), `n4`, `n4_highway`, `random["total_tested"|"total_highway"|"longest_onset"]`, `adversarial` (None or dict with `longest_onset`, `cap_hits`, `n_tested`), `obstacle` (the Appendix A object: `placements`, `hits`, `hits_rebuilt_highway`, mapped from `adversarial.obstacle_attack`), `histogram_log_bins` (4x4, list of `{lo, hi, count}`), `stubborn_k` / `stubborn_onset` / `stubborn_onset_fmt` / `stubborn_cells` / `stubborn_n_configs` / `stubborn_hist` (the S12 run: the provable 5x5 maximum and its histogram), `longest_onset`, `longest_onset_fmt`, `longest_cells`, `longest_source` (caption string), `longest_origin`, `longest_box_k` (the S12 secondary line), `total_tested`, `total_tested_fmt`, `total_highway`, `exceptions`, `cap_hits`, `show_k5` (5x5 side bar allowed only when True), `mosaic_tiles` (STORYBOARD 3.3 rows: `row, col, delay, cfg, cells, dir`, plus `onset_derived` once the tile run exists), `provisional`.
* `ctx.runs` — `common.RunCache`. Run ids: `"empty"`, `"stubborn"` (S12), `"walls"` (empty grid + the 3x3 block of `common.WALLS_PLACEMENT`; `common.walls_schedule()` is its displayed step per local frame), `"mosaic0"`..`"mosaic5"`, `"longest"` (assert-only, `ctx.runs.assert_longest_anywhere()`).
  * `ctx.runs.player(rid)` → `common.AgePlayer` (one shared instance per run: **always `seek()` before rendering**; seeking backwards is allowed but costs a rebuild).
  * `ctx.runs.stats(rid)` → `RunStats` with `bbox_at(k)` = (xmin, ymin, xmax, ymax) of cells modified in steps 1..k (incl. initial black cells) and `centroid_at(k)` = centre of those cells ("blob centre").
  * `ctx.runs.turns(rid)` → uint8 array, `turns[k-1]` is step k (1 = R, 0 = L). `ctx.runs.onset(rid)` → onset step (asserted against the facts / k4_records).
  * `ctx.runs.run(rid)` → `core.AntRun` (`pos[k]` = ant after k steps, `dir[k]`).
* `ctx.schedule` / `ctx.step_at(frame)` — displayed step of the empty-grid run per absolute frame (STORYBOARD 3.1, frame-exact: frame 15 and 480 = onset, S07/S08 = +104 per frame, S14 = +10 per frame, S15 mirrors S01). `ctx.steps_drawn(frame)` = steps advanced since the previous frame (pass it to `render_run` for the contrast cap).
* `ctx.k4` — `{"cfg", "status", "s", "dir"}` int arrays indexed by config index, read from the committed `research/results/exhaustive_k4_records.npz` (fallback: `k4_records.csv`); `status == 0` = certified. Use for the dot wall; `ctx.runs` asserts every mosaic tile's onset against it.
* `ctx.preview` — True on half-resolution preview renders (do not change the picture, only optional shortcuts).
* `ctx.shot` — `id, t0, t1, f0, f1`; `ctx.local_frame(frame)`.

### 3.2 Timing helpers
* `ctx.at(frame, t_abs)` → True on exactly the frame where absolute time `t_abs` lands: emit one-shot events with it, e.g. `if ctx.at(frame, 30.0): events.append({"type": "bell"})`.
* `common.frame_of(t)`, `common.card_anim(t, t0, t1, snap_in=False)` → `(opacity, dy)` with the 150 ms fades and 12 px drift (hero slams: `snap_in=True`).
* Easing: `core.smoothstep`, `core.ease_out_cubic`, `core.lerp`, `core.clamp`.

### 3.3 Drawing helpers (all in `common`)
* `new_frame(color=BG)`; `blend_frames(base, top, opacity)`.
* `render_run(player, cam, size=(W, H), *, steps_drawn=0, visited=True, trail=True, ant=True, gap=True, contrast_cap=None, ant_glow=1.0)` — the grid through a `core.Camera(cx, cy, cells_across)`: amber (< 1,040 steps since last flip) / cream, visited tint (>= 4 px/cell), ant trail (4 <= px/cell < 40, fading in over 40 -> 30 px), hairline grid (>= 20 px/cell), `ant_glow` scales the ant's halo (S12's static beat uses 0.25), 60 % contrast cap when `steps_drawn > 100` (or `contrast_cap=True`), 4x BOX supersampling below 4 px/cell. Mosaic tiles: `size=(360, 360), visited=False, trail=False`.
* `draw_ant_marker`, `draw_trail` if you compose your own grid picture.
* Text: `Line(text, role, size, color=CREAM, spans={"RIGHT": AMBER}, gap_before=0)`; `draw_card(img, lines, top=| center_y=, cx=520, x_left=, align="center"|"left", opacity, dy, band=True)` → band box. Every string goes through `fit_font` (shrinks by 4 px until <= 880 px, logged); every band rectangle is clamped to x 80..960 (`clamp_band_x`; use it in any private band helper too). Roles: `"bold"`, `"regular"`, `"mono"`.
* `draw_pill(img, "PROVEN"|"UNPROVEN"|"OPEN", x, y, opacity)` → box (Bold 56, radius 28, pad 20x8).
* `draw_counter(img, step, x=100, y=1520, size=60, running=True, prefix="step ", suffix="", opacity=1)` — `y` is the vertical **centre** of the text; amber running / cream frozen.
* `draw_turn_strip(img, turns, end_step, ...)` — S07 barcode of the last 208 turns with the 104-tick bracket + loop arrow (occupies y 1432..1548).
* `draw_bar_chart(img, bins, box=(100,1240,940,1560), markers=[(value, label, color)], title=...)`.
* `draw_dot_wall(img, status, n_filled, box=(136,470,904,1238), flash=0.0)`.
* `fmt_int(n)` — thousands separators. Palette constants: `BG GAP VISITED CREAM AMBER BLUE GREEN RED SECONDARY PLAIN`; safe zone `SAFE_X0..SAFE_Y1`, `SAFE_CX = 520`.

### 3.4 Camera helpers
* `cam_static(cx, cy, cells_across)`, `cam_follow(player, cells_across)`, `cam_tween(a, b, u)` (smoothstep, geometric zoom), `cam_pullback(ant_xy, blob_cxy)` (auto pull-back rule 2.5), `cam_anchor(cell_xy, screen_xy, cells_across)` (put a cell point on a screen point; S12's stage fit is `scenes_evidence._s12_fit` on top of it).
* `ctx.lag.value(key, frame, f0, target_fn)` — 0.3 s exponential lag of any vector, replayed deterministically from frame `f0` (use `ctx.shot.f0`); e.g. `cx, cy = ctx.lag.value("s05_center", frame, ctx.shot.f0, lambda f: stats.centroid_at(ctx.step_at(f)))`.
* Camera centres in S01/S07/S08/S15 must be derived from `ctx.facts.highway_sign`, not hard-coded.

## 4. Audio directive vocabulary

### 4.1 Per-frame state — build it with `common.audio_state(...)`
```python
audio_state(
  osc   = [{"run": "empty", "step": 12345, "gain_db": -16.0}, ...],   # turn-stream voices; [] = silent. A list, or one dict.
  pad   = {"chord": "chaos", "cutoff": 400.0, "detune_cents": 0.0, "gain_db": -20.0} | None,
  drone = {"on": True, "gain_db": -24.0, "add_e": False},              # default: on at -24 dBFS
  noise = {"gain_db": -30.0, "cutoff": 3000.0} | None,                  # S11 filtered-noise shimmer
  mute  = False,                                                        # True = hard silence this frame (S06 16.0-16.4)
)
```
* `osc.step` = the step the viewer is looking at for that run (the read head is re-synced to it, STORYBOARD 4.1). Levels: −20→−16 dBFS across S05, −14 in S07/S08, −26 per mosaic tile, −22 in S13; omit the voice (empty list) during S06 silence, S09, S11. Optional `"rate_mult": 2.0` doubles both read-head rates (104-periodic data sounds at 440 Hz instead of 220: the WALLS rebuilt road).
* `pad.chord`: `"chaos"` (A2 Bb3 E4 F4), `"highway"` (A2 E3 A3 C#4 E4), `"highway_shimmer"` (+A5 E6), `"lone_a2"`, `"rub"` (A2 Bb2), `"climb_a2"`, `"climb_cs3"`, `"climb_e3"`, `"off"`, or an explicit list of note names / Hz. `cutoff` in Hz, `detune_cents` drift (+8 by the end of S05).
* `drone.add_e` adds E (82.4 Hz) from S04. `drone.on=False` turns it off (S06 silence).
* Returning `None` or `{}` as the state means "defaults" (drone on, nothing else).

### 4.2 One-shot events — list of dicts, `frame` defaults to the current frame
| type | extra keys | sound (STORYBOARD 4.2 / 4.4) |
|---|---|---|
| `thump` | | 48 Hz sub thump, 250 ms (onset frames S01 0.5, S07 20.0, S12 55.4, S15 73.5; the WALLS impact 58.0) |
| `thump_long` | `tail` (s, default 2.0) | 48 Hz thump with a 2 s tail (S06 16.4) |
| `kick` | | 48 Hz, 120 ms (S07 once per second) |
| `pluck` | `turn: "R"|"L"` **or** `run, step` (turn looked up) ; optional `gain_db` | R = E4, L = A3 pluck + 3 ms click (S02-S04, S15) |
| `click` | | single 3 ms band-passed click |
| `click_cluster` | | 5 clicks over 40 ms (S09 re-rolls) |
| `knock` | | 150 Hz wooden knock (S09 lock) |
| `bell` | `freq` (default 880), `decay` (2.0) | clean A4 bell (PROVEN pills) |
| `blip` | `note` ("A4".."A5") or `freq` | 300 ms pentatonic blip (S10 certifications) |
| `riser` | `dur` (3.0) | noise band-pass sweep 200 Hz→8 kHz at −24 dBFS (S08 card A) |
| `chord_hit` | | A-major hit, 1.5 s tail (S11 47.5) |
| `micro_tick` | `n` (ticks this frame) | dot ticks, rate-limited to 200/s by the engine (S11) |
| `slot_click` | | side-bar slot click (S11) |
| `tick` | | dry 2 kHz clock tick (S12 every 0.5 s) |
| `thud` | | filtered 120 Hz thud (S13 lines, the WALLS block drop) |

Emit each event on exactly one frame (`ctx.at`). Unknown types abort the audio build.

## 5. Rules that render.py enforces or expects
* Image size 1080x1920 RGB, else the render aborts.
* Text: bands centred on x = 520; everything textual inside x 80..960, y 240..1600 (check with `--safe-zone`).
* Never hard-code a research number: use `ctx.facts`. `ctx.facts.show_k5` gates the 5x5 side bar; `ctx.facts.cap_hits > 0` triggers the S13 honesty line. Claude speaks in first person exactly once (S10 card A); no other line may.
* Test a shot: `PYTHONPATH=. python3 render.py --facts build/movie_facts.provisional.json --out build/S07.mp4 --shots S07 --preview --dump-frames build/frames_S07` then view a 540x960 PNG. Then `python3 audio.py --timeline build/timeline.json --wav build/S07.wav --mux build/S07.mp4 --out build/S07_final.mp4`.
