"""Shared layer for the "Two Rules, One Road" renderer.

Everything the two scene modules (scenes_road.py, scenes_evidence.py) need
and nothing scene-specific:

  * facts loading + validation (STORYBOARD section 6), including the derived
    LONGEST_* / TOTAL_TESTED values and the exact splitmix64 regeneration of a
    random configuration given only (k, p, seed, index);
  * the run cache (empty grid, longest-delay run, mosaic tiles) with on-disk
    memoisation under build/runs/;
  * AgePlayer: a GridPlayer that also knows the step of every cell's last flip,
    so render_run() can paint fresh ink amber and old ink cream;
  * render_run(): the grid renderer with visited tint, ant trail, contrast cap,
    hairline grid and BOX supersampling below 4 px/cell;
  * the frame-exact step schedule of the empty-grid run (STORYBOARD 3.1);
  * text / UI helpers (band cards, fit-or-shrink, pills, counters, turn strip,
    bar chart, dot wall) and the camera helpers of STORYBOARD 2.5.

Coordinates follow research/CONVENTIONS.md: x East, y North (= UP on screen).
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import core
from core import Camera, clamp, smoothstep, lerp

# --------------------------------------------------------------------------
# Constants (STORYBOARD 1, 2.1, 2.3)
# --------------------------------------------------------------------------

W, H, FPS = 1080, 1920, 30
DURATION_S = 74.0
N_FRAMES = int(round(DURATION_S * FPS))  # 2220

SAFE_X0, SAFE_Y0, SAFE_X1, SAFE_Y1 = 80, 240, 960, 1600
SAFE_CX = 520            # text bands are centred here, NOT on 540
MAX_TEXT_W = 880         # every drawn line must measure <= this

MOVIE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(MOVIE_DIR)
BUILD_DIR = os.path.join(MOVIE_DIR, "build")

hex_rgb = core.hex_rgb

BG = hex_rgb("#12141B")          # "white" (empty) cell, drawn dark
GAP = hex_rgb("#1C1F28")         # hairline grid
VISITED = hex_rgb("#1A1D26")     # visited-but-empty tint
CREAM = hex_rgb("#F4EFE3")       # old black cell, primary text, frozen counter
AMBER = hex_rgb("#FFB84D")       # fresh black cell, accent, running counter
BLUE = hex_rgb("#3D8BFF")        # ant
GREEN = hex_rgb("#4CD97B")       # PROVEN pill
RED = hex_rgb("#FF4D4D")         # uncertified / cap-hit
SECONDARY = hex_rgb("#A8A49B")   # captions, citations, credit
PLAIN = hex_rgb("#0B0D12")       # plain card background, band fill, pill text

PALETTE = {
    "bg": BG, "gap": GAP, "visited": VISITED, "cream": CREAM, "amber": AMBER,
    "blue": BLUE, "green": GREEN, "red": RED, "secondary": SECONDARY, "plain": PLAIN,
}

AGE_FRESH = 1040            # steps: age < 1040 -> amber, else cream (10 periods)
CAP_STEPS_PER_FRAME = 100   # > 100 steps drawn per frame -> 60 % contrast cap
CAP_BLEND = 0.4             # blend black cells 40 % toward the background
TRAIL_LEN = 20              # last 20 ant positions

BAND_ALPHA, BAND_RADIUS, BAND_PAD = 0.85, 24, 28
LINE_SPACING = 1.15

TEXT_FADE = 0.15            # s, fade in / out of cards
TEXT_DRIFT = 12             # px upward drift on fade in


def frame_of(t: float) -> int:
    """Frame index of absolute time t (STORYBOARD: frame = round(t*30)); half-up rounding
    (never banker's rounding) so a future .5 tie such as 7.35 s cannot map one frame early."""
    return int(math.floor(t * FPS + 0.5 + 1e-9))


def fmt_int(n: int) -> str:
    """Thousands separators: 9977 -> '9,977'."""
    return f"{int(n):,}"


# --------------------------------------------------------------------------
# Facts (STORYBOARD section 6)
# --------------------------------------------------------------------------

class FactsError(RuntimeError):
    """Raised when movie_facts.json is missing or inconsistent. Never substitute."""


def _get(d: dict, path: str):
    """Fetch a dotted path from nested dicts, raising FactsError naming the field."""
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise FactsError(f"movie_facts: missing required field '{path}'")
        cur = cur[part]
    return cur


def splitmix_config(k: int, p: float, seed: int, idx: int) -> list[tuple[int, int]]:
    """Exact re-implementation of research/random/randexp.c gen_config().

    Cells are visited in order i = 0..k*k-1, (x, y) = (xmin + i % k, xmin + i // k),
    xmin = -(k // 2); splitmix64 seeded with the documented mix; black iff
    (r >> 11) * 2^-53 < p.
    """
    M = (1 << 64) - 1
    p1000 = int(round(1000.0 * p))
    state = (seed * 0x9E3779B97F4A7C15 + idx * 0xBF58476D1CE4E5B9
             + k * 0x94D049BB133111EB + p1000 * 0xD6E8FEB86659FD93) & M
    xmin = -(k // 2)
    cells = []
    for i in range(k * k):
        state = (state + 0x9E3779B97F4A7C15) & M
        z = state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M
        z = z ^ (z >> 31)
        u = (z >> 11) * (1.0 / 9007199254740992.0)
        if u < p:
            cells.append((xmin + i % k, xmin + i // k))
    return cells


def _config_cells(obj: dict, field_path: str) -> list[tuple[int, int]]:
    """Black-cell list of a config object: explicit `black_cells`, else regenerated
    from the (k, p, seed, index) tuple with the exact randexp RNG."""
    if "black_cells" in obj:
        return [tuple(int(v) for v in c) for c in obj["black_cells"]]
    for key in ("k", "p", "seed", "index"):
        if key not in obj:
            raise FactsError(f"movie_facts: '{field_path}' needs black_cells or (k,p,seed,index); missing '{key}'")
    cells = splitmix_config(int(obj["k"]), float(obj["p"]), int(obj["seed"]), int(obj["index"]))
    if "n_black" in obj and int(obj["n_black"]) != len(cells):
        raise FactsError(f"movie_facts: '{field_path}' regenerated {len(cells)} cells, expected n_black={obj['n_black']}")
    return cells


@dataclass
class Facts:
    """Validated movie facts plus every derived placeholder of STORYBOARD 6."""

    path: str
    raw: dict
    provisional: bool
    onset: int                       # {ONSET_STEP}
    period: int                      # {PERIOD} == 104
    displacement: tuple[int, int]    # {DISPLACEMENT}
    direction: str                   # {HIGHWAY_DIR}
    exhaustive: dict                 # {"1": {...}, ..., "5": {...}} as given
    random: dict
    adversarial: dict | None
    obstacle: dict | None
    histogram_log_bins: list         # exhaustive["4"].histogram_log_bins
    longest_onset: int               # {LONGEST_ONSET}
    longest_cells: list[tuple[int, int]]
    longest_source: str              # {LONGEST_SOURCE} caption
    longest_origin: str              # 'adversarial' | 'exhaustive' | 'random'
    total_tested: int                # {TOTAL_TESTED}
    total_highway: int
    cap_hits: int                    # {CAP_HITS} (0 when no adversarial object)
    show_k5: bool                    # 5x5 side bar allowed?
    mosaic_tiles: list               # STORYBOARD 3.3 rows (cells + cfg index)
    k4_records_csv: str | None

    # convenience -----------------------------------------------------------
    @property
    def onset_fmt(self) -> str:
        return fmt_int(self.onset)

    @property
    def longest_onset_fmt(self) -> str:
        return fmt_int(self.longest_onset)

    @property
    def total_tested_fmt(self) -> str:
        return fmt_int(self.total_tested)

    @property
    def exceptions(self) -> int:
        return self.total_tested - self.total_highway

    def exh(self, k: int | str) -> dict | None:
        return self.exhaustive.get(str(k))

    @property
    def n4(self) -> int:
        return int(self.exhaustive["4"]["n_configs"])

    @property
    def n4_highway(self) -> int:
        return int(self.exhaustive["4"]["n_highway"])

    @property
    def highway_sign(self) -> tuple[int, int]:
        """(sx, sy) = sign of the per-period displacement (-1,-1 = lower-left)."""
        return (int(np.sign(self.displacement[0])), int(np.sign(self.displacement[1])))


# STORYBOARD 3.3: six real 4x4 configs (row, col, delay, cfg index, cells, expected onset,
# direction).  Static in the storyboard; the renderer re-derives every onset with
# core.find_onset and asserts it against k4_records.csv.
MOSAIC_TILES = [
    {"row": 1, "col": 1, "delay": 0.0, "cfg": 45206, "onset": 19039, "dir": "-x,-y",
     "cells": [(-1, -2), (0, -2), (-2, -1), (1, -1), (-2, 1), (-1, 1), (1, 1)]},
    {"row": 1, "col": 2, "delay": 0.4, "cfg": 31091, "onset": 14014, "dir": "-x,+y",
     "cells": [(-2, -2), (-1, -2), (-2, -1), (-1, -1), (0, -1), (-2, 0), (1, 0), (-2, 1), (-1, 1), (0, 1)]},
    {"row": 2, "col": 1, "delay": 0.8, "cfg": 21144, "onset": 9002, "dir": "+x,-y",
     "cells": [(1, -2), (-2, -1), (1, -1), (-1, 0), (-2, 1), (0, 1)]},
    {"row": 2, "col": 2, "delay": 1.2, "cfg": 8636, "onset": 4002, "dir": "+x,+y",
     "cells": [(0, -2), (1, -2), (-2, -1), (-1, -1), (1, -1), (-2, 0), (-1, 1)]},
    {"row": 3, "col": 1, "delay": 1.6, "cfg": 6362, "onset": 2501, "dir": "-x,-y",
     "cells": [(-1, -2), (1, -2), (-2, -1), (0, -1), (1, -1), (1, 0), (-2, 1)]},
    {"row": 3, "col": 2, "delay": 2.0, "cfg": 6077, "onset": 1000, "dir": "+x,+y",
     "cells": [(-2, -2), (0, -2), (1, -2), (-2, -1), (-1, -1), (1, -1), (-2, 0), (-1, 0), (0, 0), (-2, 1)]},
]


# Priority on an exact onset tie between candidates for {LONGEST_ONSET}: an exhaustive
# maximum is a provable statement about its box, a random sample is an unbiased draw, and a
# search that only re-found one of them added nothing - so exhaustive > random > adversarial.
_ORIGIN_PRIORITY = {"exhaustive": 3, "random": 2, "adversarial": 1}

_RANDOM_SUMMARY_RE = re.compile(
    r"k=(?P<k>\d+),\s*p=(?P<p>[0-9.]+),\s*seed\s+(?P<seed>\d+),\s*sample_index\s+(?P<index>\d+),\s*(?P<n_black>\d+)\s+black cells")


def _load_results_json(raw: dict, section: str, default: str) -> dict:
    """Open the research result file a facts section points to (`<section>.source`)."""
    rel = raw.get(section, {}).get("source", default) if isinstance(raw.get(section), dict) else default
    path = rel if os.path.isabs(rel) else os.path.join(REPO_DIR, rel)
    if not os.path.exists(path):
        raise FactsError(f"movie_facts: '{section}.source' file not found: {path}")
    with open(path) as fh:
        return json.load(fh)


def adapt_verified_schema(raw: dict) -> dict:
    """Map the verified research/results/movie_facts.json layout onto the STORYBOARD
    section-6 field names.  Explicit, one-way, and it never invents a number:

      exhaustive.kN -> exhaustive.N (non-dict bookkeeping keys dropped), n_cap -> cap_hits;
      exhaustive.4.histogram_log_bins and k4_records_csv, when absent, are read from the
        exhaustive result file named by exhaustive.source (STORYBOARD section 5);
      random.longest_config, when absent, is the (k, p, seed, index, n_black) tuple parsed
        from random.longest_config_summary (the renderer regenerates the cells with the exact
        randexp RNG and asserts the onset by re-simulation);
      random.max_k, when absent, is the largest k of any random sweep table;
      adversarial.n_tested <- adversarial.total_runs.

    A section-6 file passes through unchanged.  Fields that stay missing are reported by
    load_facts by name, as before.
    """
    raw = json.loads(json.dumps(raw))          # deep copy; never mutate the caller's dict
    exh = raw.get("exhaustive")
    if isinstance(exh, dict):
        mapped = {}
        for key, entry in exh.items():
            if not isinstance(entry, dict):
                continue
            k = str(entry.get("k", key[1:] if re.fullmatch(r"k\d+", key) else key))
            if "cap_hits" not in entry and "n_cap" in entry:
                entry["cap_hits"] = entry["n_cap"]
            mapped[k] = entry
        if "source" in exh:
            mapped["source"] = exh["source"]
        raw["exhaustive"] = mapped
        e4 = mapped.get("4")
        if isinstance(e4, dict) and ("histogram_log_bins" not in e4 or "k4_records_csv" not in raw):
            res4 = _get(_load_results_json(raw, "exhaustive", "research/results/exhaustive.json"), "results.k4")
            e4.setdefault("histogram_log_bins", res4.get("histogram_log_bins"))
            if "k4_records_csv" not in raw and "per_config_csv" in res4:
                raw["k4_records_csv"] = res4["per_config_csv"]
    rnd = raw.get("random")
    if isinstance(rnd, dict):
        if "longest_config" not in rnd and "longest_config_summary" in rnd:
            m = _RANDOM_SUMMARY_RE.search(str(rnd["longest_config_summary"]))
            if not m:
                raise FactsError("movie_facts: random.longest_config_summary does not name (k, p, seed, sample_index, n black cells)")
            rnd["longest_config"] = {"k": int(m["k"]), "p": float(m["p"]), "seed": int(m["seed"]),
                                     "index": int(m["index"]), "n_black": int(m["n_black"])}
        if "max_k" not in rnd:
            ks = list(rnd.get("k_values", [])) + list(rnd.get("main_sweep", {}).get("k_values", []))
            for name, table in rnd.items():
                if name.startswith("median_onset") and isinstance(table, dict):
                    ks += [int(k) for k in table if str(k).isdigit()]
            if isinstance(rnd.get("longest_config"), dict) and "k" in rnd["longest_config"]:
                ks.append(int(rnd["longest_config"]["k"]))
            if ks:
                rnd["max_k"] = int(max(ks))
    adv = raw.get("adversarial")
    if isinstance(adv, dict) and "n_tested" not in adv and "total_runs" in adv:
        adv["n_tested"] = adv["total_runs"]
    return raw


def load_facts(path: str) -> Facts:
    """Load and validate movie_facts.json; derive the section-6 placeholders.

    Aborts (FactsError) naming the first missing field.  Nothing is ever
    substituted.  The verified file's layout is mapped by adapt_verified_schema.
    The longest configuration is regenerated from its tuple when no cell list is
    given; its onset is asserted later by RunCache.longest().
    """
    if not os.path.exists(path):
        raise FactsError(f"movie_facts: file not found: {path}")
    with open(path) as fh:
        raw = adapt_verified_schema(json.load(fh))

    onset = int(_get(raw, "onset_step_empty_grid"))
    period = int(_get(raw, "period"))
    if period != 104:
        raise FactsError(f"movie_facts: period must be 104, got {period}")
    disp = _get(raw, "displacement_per_period")
    if not (isinstance(disp, (list, tuple)) and len(disp) == 2):
        raise FactsError("movie_facts: displacement_per_period must be [dx, dy]")
    disp = (int(disp[0]), int(disp[1]))
    direction = str(_get(raw, "direction_empty_grid"))
    expect_dir = f"{'+' if disp[0] > 0 else '-'}x,{'+' if disp[1] > 0 else '-'}y"
    if direction.replace("−", "-") != expect_dir:
        raise FactsError(f"movie_facts: direction_empty_grid {direction!r} disagrees with displacement {disp}")

    exhaustive = {k: e for k, e in _get(raw, "exhaustive").items() if isinstance(e, dict)}
    if "4" not in exhaustive:
        raise FactsError("movie_facts: missing required field 'exhaustive.4'")
    for k, e in exhaustive.items():
        for f in ("n_configs", "n_highway", "max_onset", "cap_hits"):
            _get(raw, f"exhaustive.{k}.{f}")
    hist = _get(raw, "exhaustive.4.histogram_log_bins")
    rnd = _get(raw, "random")
    for f in ("total_tested", "total_highway", "longest_onset", "longest_config"):
        _get(raw, f"random.{f}")
    adv = raw.get("adversarial")
    if adv is not None:
        for f in ("longest_onset", "cap_hits", "n_tested"):
            _get(raw, f"adversarial.{f}")

    # LONGEST_* : max over the candidates; exact ties -> _ORIGIN_PRIORITY.  A candidate may
    # lack its cell list; that is fatal only if it wins.
    cands = []  # (onset, priority, origin, config or None, config path, source caption)
    if adv is not None:
        cfg = adv.get("longest_config")
        box = cfg.get("box_k") if cfg else None
        n_cells = len(_config_cells(cfg, "adversarial.longest_config")) if cfg else "?"
        cap = f"evolved · {box}x{box} box · {n_cells} cells" if box else f"evolved · {n_cells} cells"
        cands.append((int(adv["longest_onset"]), "adversarial", cfg, "adversarial.longest_config", cap))
    for k, e in exhaustive.items():
        cfg = e.get("max_onset_config")
        cap = f"{k}x{k} box · pattern {fmt_int(cfg.get('cfg_index', 0))}" if cfg else f"{k}x{k} box"
        cands.append((int(e["max_onset"]), "exhaustive", cfg, f"exhaustive.{k}.max_onset_config", cap))
    rcfg = rnd["longest_config"]
    rcap = f"index {rcfg.get('index', '?')} · {rcfg.get('k', '?')}x{rcfg.get('k', '?')} · p={rcfg.get('p', '?')}"
    cands.append((int(rnd["longest_onset"]), "random", rcfg, "random.longest_config", rcap))
    longest_onset, origin, cfg, cfg_path, source = max(cands, key=lambda c: (c[0], _ORIGIN_PRIORITY[c[1]]))
    if cfg is None:
        raise FactsError(f"movie_facts: missing required field '{cfg_path}' (the {origin} record holds LONGEST_ONSET)")
    longest_cells = _config_cells(cfg, cfg_path)

    # TOTAL_* : section-6 sum (exhaustive boxes are nested and the adversarial count is
    # evaluations, so this counts RUNS - S13 says so); cross-checked against the verified total.
    total_tested = sum(int(e["n_configs"]) for e in exhaustive.values()) + int(rnd["total_tested"])
    total_highway = sum(int(e["n_highway"]) for e in exhaustive.values()) + int(rnd["total_highway"])
    cap_hits = 0
    if adv is not None:
        total_tested += int(adv["n_tested"])
        total_highway += int(adv.get("n_highway", int(adv["n_tested"]) - int(adv["cap_hits"])))
        cap_hits = int(adv["cap_hits"])
    if "total_runs_all_experiments" in raw and int(raw["total_runs_all_experiments"]) != total_tested:
        raise FactsError(f"movie_facts: total_runs_all_experiments={raw['total_runs_all_experiments']} "
                         f"but the section-6 sum is {total_tested}")
    if "total_runs_non_certified" in raw and int(raw["total_runs_non_certified"]) != total_tested - total_highway:
        raise FactsError("movie_facts: total_runs_non_certified disagrees with the section-6 sums")
    e5 = exhaustive.get("5")
    show_k5 = bool(e5 and int(e5["n_highway"]) == int(e5["n_configs"]) == 33_554_432 and int(e5["cap_hits"]) == 0)

    tiles = raw.get("mosaic_tiles") or MOSAIC_TILES
    tiles = [dict(t, cells=[tuple(int(v) for v in c) for c in t["cells"]]) for t in tiles]

    return Facts(
        path=path, raw=raw, provisional=bool(raw.get("provisional", False)),
        onset=onset, period=period, displacement=disp, direction=direction,
        exhaustive=exhaustive, random=rnd, adversarial=adv, obstacle=raw.get("obstacle"),
        histogram_log_bins=hist, longest_onset=longest_onset, longest_cells=longest_cells,
        longest_source=source, longest_origin=origin, total_tested=total_tested,
        total_highway=total_highway, cap_hits=cap_hits, show_k5=show_k5, mosaic_tiles=tiles,
        k4_records_csv=raw.get("k4_records_csv"),
    )


# --------------------------------------------------------------------------
# k4 records (dot wall status + mosaic onset assertion)
# --------------------------------------------------------------------------

# The per-config CSV is derived data (gitignored); this command rebuilds it in a few seconds.
K4_RECORDS_REGEN = ("cd research/exhaustive && gcc -O3 -march=native -o exhaust exhaust.c && "
                    "mkdir -p out && ./exhaust 4 0 65536 5000000 out/k4 1")


def load_k4_records(path: str) -> dict:
    """Read research/exhaustive/out/k4_records.csv -> {'cfg', 'status', 's'} int arrays.

    status 0 = certified highway.  Cached as an .npz under build/ (the CSV is 7 MB).
    """
    path = os.path.join(REPO_DIR, path) if not os.path.isabs(path) else path
    if not os.path.exists(path):
        raise FactsError(f"k4 records CSV not found: {path} (it is not committed; regenerate it with "
                         f"{K4_RECORDS_REGEN})")
    cache = os.path.join(BUILD_DIR, "runs", "k4_records.npz")
    if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(path):
        z = np.load(cache)
        return {"cfg": z["cfg"], "status": z["status"], "s": z["s"]}
    cfg, status, s = [], [], []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            cfg.append(int(row["cfg"]))
            status.append(int(row["status"]))
            s.append(int(row["s"]))
    rec = {"cfg": np.array(cfg, dtype=np.int64), "status": np.array(status, dtype=np.int16), "s": np.array(s, dtype=np.int64)}
    order = np.argsort(rec["cfg"])
    rec = {k: v[order] for k, v in rec.items()}
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    np.savez(cache, **rec)
    return rec


# --------------------------------------------------------------------------
# Runs: cache + player + per-run statistics
# --------------------------------------------------------------------------

def _run_key(cells, n_steps: int, size: int) -> str:
    h = hashlib.sha1(json.dumps([sorted(map(list, cells)), n_steps, size]).encode()).hexdigest()[:16]
    return f"run_{h}"


def simulate_cached(cells, n_steps: int, size: int) -> core.AntRun:
    """core.simulate with an .npz memo under build/runs/ (pos, dir, turns)."""
    cells = [tuple(int(v) for v in c) for c in cells]
    path = os.path.join(BUILD_DIR, "runs", _run_key(cells, n_steps, size) + ".npz")
    if os.path.exists(path):
        z = np.load(path)
        pos, dirs, turns = z["pos"], z["dir"], z["turns"]
        off = size // 2
        grid = np.zeros((size, size), dtype=np.uint8)
        visited = np.zeros((size, size), dtype=np.int32)
        for (x, y) in cells:
            grid[y + off, x + off] = 1
        gy, gx = pos[:-1, 1] + off, pos[:-1, 0] + off
        np.bitwise_xor.at(grid, (gy, gx), np.uint8(1))
        np.add.at(visited, (gy, gx), 1)
        return core.AntRun(size, off, pos, dirs, turns, grid, visited, cells)
    run = core.simulate(n_steps, cells, size=size)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez(path, pos=run.pos, dir=run.dir, turns=run.turns)
    return run


class RunStats:
    """Prefix statistics of a run: bbox and centroid of the cells modified in steps 1..k."""

    def __init__(self, run: core.AntRun):
        p = run.pos[:-1]  # pos[k] is the cell modified at step k+1
        init = np.array(run.initial_black, dtype=np.int64).reshape(-1, 2)
        xs, ys = p[:, 0], p[:, 1]
        self.n = len(p)
        self.minx = np.minimum.accumulate(xs)
        self.maxx = np.maximum.accumulate(xs)
        self.miny = np.minimum.accumulate(ys)
        self.maxy = np.maximum.accumulate(ys)
        self.init_bbox = None
        if len(init):
            self.init_bbox = (init[:, 0].min(), init[:, 1].min(), init[:, 0].max(), init[:, 1].max())
        key = (xs - xs.min()).astype(np.int64) * (ys.max() - ys.min() + 1) + (ys - ys.min())
        _, first = np.unique(key, return_index=True)
        mask = np.zeros(self.n, dtype=np.float64)
        mask[first] = 1.0
        self.cnt = np.cumsum(mask)
        self.sx = np.cumsum(xs * mask)
        self.sy = np.cumsum(ys * mask)

    def bbox_at(self, k: int) -> tuple[float, float, float, float]:
        """(xmin, ymin, xmax, ymax) of cells modified in steps 1..k (incl. initial black cells)."""
        k = int(clamp(k, 1, self.n))
        b = (self.minx[k - 1], self.miny[k - 1], self.maxx[k - 1], self.maxy[k - 1])
        if self.init_bbox is not None:
            b = (min(b[0], self.init_bbox[0]), min(b[1], self.init_bbox[1]), max(b[2], self.init_bbox[2]), max(b[3], self.init_bbox[3]))
        return tuple(float(v) for v in b)

    def centroid_at(self, k: int) -> tuple[float, float]:
        """Centre of the distinct cells modified in steps 1..k (cell centres)."""
        k = int(clamp(k, 1, self.n))
        c = self.cnt[k - 1]
        return (self.sx[k - 1] / c + 0.5, self.sy[k - 1] / c + 0.5)


class AgePlayer(core.GridPlayer):
    """GridPlayer with a correct `last_flip` array after any seek.

    Forward seeks are vectorised; a backward seek rebuilds from step 0 so that
    `visited` and `last_flip` are exact (core.GridPlayer's involution trick
    cannot restore a cell's previous flip step).
    """

    def __init__(self, run: core.AntRun):
        super().__init__(run)
        self.last_flip = self.age  # alias: core stores the step index of the last flip here
        self.last_flip.fill(-(10 ** 9))

    def _reset(self):
        self.grid.fill(0)
        self.visited.fill(0)
        self.last_flip.fill(-(10 ** 9))
        for (x, y) in self.run.initial_black:
            self.grid[y + self.off, x + self.off] = 1
        self.k = 0

    def seek(self, k: int):
        k = int(max(0, min(k, len(self.run.turns))))
        if k < self.k:
            self._reset()
        if k == self.k:
            return
        p = self.run.pos[self.k:k]
        gy, gx = p[:, 1] + self.off, p[:, 0] + self.off
        np.bitwise_xor.at(self.grid, (gy, gx), np.uint8(1))
        self.visited[gy, gx] = 1
        np.maximum.at(self.last_flip, (gy, gx), np.arange(self.k, k, dtype=np.int32))
        self.k = k

    def trail(self, n: int = TRAIL_LEN) -> np.ndarray:
        """Last n ant positions (oldest first, current last)."""
        return self.run.pos[max(0, self.k - n + 1): self.k + 1]


LONGEST_TAIL_STEPS = 20_000   # steps simulated past LONGEST_ONSET: 48 frames x 104 + audio lookahead


class RunCache:
    """Lazily simulated runs shared by scenes and the audio engine.

    Run ids: "empty" (S01-S08, S14, S15), "longest" (S12), "mosaic0".."mosaic5" (S10).
    Every onset is asserted: the empty grid and the longest run against the facts, the
    mosaic tiles against the STORYBOARD 3.3 table and k4_records.csv.
    """

    EMPTY_STEPS = 60_000
    EMPTY_SIZE = 2048
    MOSAIC_STEPS = 40_000   # 6,000 steps/s x 6 s + audio lookahead
    MOSAIC_SIZE = 2048      # the road travels ~750 cells in 40,000 steps

    def __init__(self, facts: Facts):
        self.facts = facts
        self._runs: dict[str, core.AntRun] = {}
        self._stats: dict[str, RunStats] = {}
        self._players: dict[str, AgePlayer] = {}
        self._k4: dict | None = None
        self.longest_size = 4096

    def run(self, rid: str) -> core.AntRun:
        if rid in self._runs:
            return self._runs[rid]
        if rid == "empty":
            r = simulate_cached((), self.EMPTY_STEPS, self.EMPTY_SIZE)
            got = core.find_onset(r.turns)
            if got != self.facts.onset:
                raise FactsError(f"empty-grid onset re-simulated as {got}, facts say {self.facts.onset}")
        elif rid == "longest":
            r = self._simulate_longest()
        elif rid.startswith("mosaic"):
            i = int(rid[len("mosaic"):])
            tile = self.facts.mosaic_tiles[i]
            r = simulate_cached(tile["cells"], self.MOSAIC_STEPS, self.MOSAIC_SIZE)
            got = core.find_onset(r.turns)
            if got < 0 or ("onset" in tile and got != int(tile["onset"])):
                raise FactsError(f"mosaic tile {i} (cfg {tile['cfg']}) onset re-derived as {got}, table says {tile.get('onset')}")
            self._assert_k4_record(i, int(tile["cfg"]), got)
            tile["onset_derived"] = got
        else:
            raise KeyError(rid)
        self._runs[rid] = r
        return r

    def k4(self) -> dict:
        """The k4_records.csv arrays {'cfg', 'status', 's'} (dot wall + mosaic assertions)."""
        if self._k4 is None:
            if not self.facts.k4_records_csv:
                raise FactsError("movie_facts: missing required field 'k4_records_csv'")
            self._k4 = load_k4_records(self.facts.k4_records_csv)
        return self._k4

    def _assert_k4_record(self, i: int, cfg: int, onset: int):
        """STORYBOARD 5: a mosaic tile's re-derived onset must equal the CSV's `s` for its
        config index, and that record must be certified (status 0)."""
        rec = self.k4()
        j = int(np.searchsorted(rec["cfg"], cfg))
        if j >= len(rec["cfg"]) or int(rec["cfg"][j]) != cfg:
            raise FactsError(f"mosaic tile {i}: cfg {cfg} not found in {self.facts.k4_records_csv}")
        if onset != int(rec["s"][j]) or int(rec["status"][j]) != 0:
            raise FactsError(f"mosaic tile {i} (cfg {cfg}): onset re-derived as {onset}, k4_records.csv says "
                             f"s={int(rec['s'][j])} status={int(rec['status'][j])}")

    def _simulate_longest(self) -> core.AntRun:
        f = self.facts
        n_steps = f.longest_onset + LONGEST_TAIL_STEPS    # S12 shows <= 104 steps/frame after the onset
        size = self.longest_size
        while True:
            r = simulate_cached(f.longest_cells, n_steps, size)
            if int(np.abs(r.pos).max()) + 64 < size // 2:
                break
            size *= 2
            self.longest_size = size
        got = core.find_onset(r.turns)
        if got != f.longest_onset:
            raise FactsError(f"longest run onset re-simulated as {got}, facts say {f.longest_onset}")
        return r

    def turns(self, rid: str) -> np.ndarray:
        return self.run(rid).turns

    def stats(self, rid: str) -> RunStats:
        if rid not in self._stats:
            self._stats[rid] = RunStats(self.run(rid))
        return self._stats[rid]

    def player(self, rid: str) -> AgePlayer:
        if rid not in self._players:
            self._players[rid] = AgePlayer(self.run(rid))
        return self._players[rid]

    def onset(self, rid: str) -> int:
        if rid == "empty":
            return self.facts.onset
        if rid == "longest":
            return self.facts.longest_onset
        self.run(rid)
        return int(self.facts.mosaic_tiles[int(rid[len("mosaic"):])]["onset_derived"])


# --------------------------------------------------------------------------
# Step schedule of the empty-grid run (STORYBOARD 3.1)
# --------------------------------------------------------------------------

def build_step_schedule(onset: int) -> np.ndarray:
    """step_at_frame[f] for f in 0..N_FRAMES-1: the displayed step of the empty-grid run.

    Integer steps per frame = floored cumulative float step counts; S05 is forced to
    land on `onset` exactly at frame 480 (rounding residual spread over frames 470-479).
    Shots that do not show the empty-grid run hold the S08 end value.
    """
    steps = np.zeros(N_FRAMES, dtype=np.int64)
    # S01 0-2 s: 3000 steps/s from onset-1500 (frame 15 = onset)
    for f in range(0, 60):
        steps[f] = onset - 1500 + 100 * f
    # S02 2.0-4.5 s: steps 1..4 at t = 2.3 + 0.5 (k-1)
    for f in range(60, 135):
        t = f / FPS
        steps[f] = sum(1 for k in range(1, 5) if f >= frame_of(2.3 + 0.5 * (k - 1)))
    # S03 4.5-7.0 s: step 5 at 4.9, 6..9 at 5.4, 5.9, 6.4, 6.9
    for f in range(135, 210):
        steps[f] = 4 + sum(1 for k in range(5, 10) if f >= frame_of(4.9 + 0.5 * (k - 5)))
    # S04 7-10 s: r(t) = 2 * 30^((t-7)/3)  -> cumulative 6/ln(30) * (30^((t-7)/3) - 1) ~ 51.17
    ln30 = math.log(30.0)
    for f in range(210, 300):
        t = f / FPS
        cum = 6.0 / ln30 * (30.0 ** ((t - 7.0) / 3.0) - 1.0)
        steps[f] = 9 + int(math.floor(cum))
    # S05 10-16 s: r(t) = 60 e^{a(t-10)}, a solved so that the integral over 6 s = onset - 60
    target = onset - 60
    lo, hi = 1e-6, 5.0
    for _ in range(200):
        a = 0.5 * (lo + hi)
        if 60.0 * (math.exp(6 * a) - 1.0) / a < target:
            lo = a
        else:
            hi = a
    a = 0.5 * (lo + hi)
    for f in range(300, 481):
        t = f / FPS
        steps[f] = 60 + int(math.floor(60.0 * (math.exp(a * (t - 10.0)) - 1.0) / a))
    residual = onset - int(steps[480])
    for i, f in enumerate(range(470, 481)):   # distribute into the last 10 frames
        steps[f] += int(round(residual * i / 10))
    steps[480] = onset
    # S06 16-20 s: frozen
    steps[480:600] = onset
    # S07 + S08 20-33 s: frame 600 resumes from the frozen onset picture, then exactly
    # 104 steps per frame; the S08 end value of the table ({ONSET}+40,560) is reached at 33.0 s
    for f in range(600, 990):
        steps[f] = onset + 104 * (f - 600)
    end_s08 = onset + 104 * 390
    # S09-S13: not shown (hold)
    steps[990:1860] = end_s08
    # S14 62-68 s: 300 steps/s (10 per frame) resuming from the S08 end
    for f in range(1860, 2040):
        steps[f] = end_s08 + 10 * (f - 1860)
    # S15 68-74 s: identical to S01
    for f in range(2040, 2220):
        steps[f] = onset - 1500 + 100 * (f - 2040)
    assert steps[15] == onset and steps[480] == onset and steps[600] == onset
    assert steps[809] == onset + 21736 and steps[989] == onset + 40456 and steps[990] == onset + 40560
    assert np.all(np.diff(steps[300:481]) >= 0)
    return steps


# --------------------------------------------------------------------------
# Grid rendering (STORYBOARD 2.1, 2.5)
# --------------------------------------------------------------------------

def _visible_window(cam: Camera, w: int, h: int):
    """Integer cell window [ix0, ix1) x [iy0, iy1) covering the w x h view, plus x0 / y_top."""
    cell_px = w / cam.cells_across
    x0 = cam.cx - cam.cells_across / 2
    y_top = cam.cy + (h / cell_px) / 2
    ix0 = int(math.floor(x0)) - 1
    ix1 = int(math.ceil(x0 + cam.cells_across)) + 2
    iy1 = int(math.ceil(y_top)) + 2
    iy0 = int(math.floor(y_top - h / cell_px)) - 1
    return cell_px, x0, y_top, ix0, ix1, iy0, iy1


def render_run(
    player: AgePlayer,
    cam: Camera,
    size: tuple[int, int] = (W, H),
    *,
    steps_drawn: int = 0,
    visited: bool = True,
    trail: bool = True,
    ant: bool = True,
    gap: bool = True,
    bg: tuple = BG,
    contrast_cap: bool | None = None,
) -> Image.Image:
    """Render the player's current grid through `cam` into a size[0] x size[1] RGB image.

    * black cells: amber if (step - last_flip) < AGE_FRESH else cream;
    * `steps_drawn` = steps advanced since the previous frame; when > 100 (or
      contrast_cap=True) black cells are blended 40 % toward the background
      (photosensitivity cap, STORYBOARD 2.5) - the amber tint is kept, only dimmed;
    * visited-but-empty tint, ant trail and hairline grid follow the px/cell rules;
    * below 4 px/cell the grid is rendered at 4x and BOX-downsampled.
    """
    w, h = size
    cell_px, x0, y_top, ix0, ix1, iy0, iy1 = _visible_window(cam, w, h)
    off, n = player.off, player.size
    gx0, gx1, gy0, gy1 = ix0 + off, ix1 + off, iy0 + off, iy1 + off
    cx0, cx1, cy0, cy1 = max(0, gx0), min(n, gx1), max(0, gy0), min(n, gy1)
    sub = player.grid[cy0:cy1, cx0:cx1]
    age = player.k - player.last_flip[cy0:cy1, cx0:cx1]
    cap = contrast_cap if contrast_cap is not None else steps_drawn > CAP_STEPS_PER_FRAME
    cream = np.array(CREAM, dtype=np.float32)
    amber = np.array(AMBER, dtype=np.float32)
    bgv = np.array(bg, dtype=np.float32)
    if cap:
        cream = cream * (1 - CAP_BLEND) + bgv * CAP_BLEND
        amber = amber * (1 - CAP_BLEND) + bgv * CAP_BLEND
    cls = np.zeros(sub.shape, dtype=np.uint8)          # 0 bg, 1 cream, 2 amber, 3 visited
    black = sub == 1
    cls[black] = 1
    cls[black & (age < AGE_FRESH)] = 2
    if visited and cell_px >= 4:
        vsub = player.visited[cy0:cy1, cx0:cx1]
        cls[(~black) & (vsub > 0)] = 3
    lut = np.array([bgv, cream, amber, np.array(VISITED, dtype=np.float32)], dtype=np.float32)
    rgb = lut[cls].astype(np.uint8)
    padh, padw = (cy0 - gy0, gy1 - cy1), (cx0 - gx0, gx1 - cx1)
    if any(padh) or any(padw):
        rgb = np.pad(rgb, (padh, padw, (0, 0)), mode="constant", constant_values=0)
        m = np.ones(rgb.shape[:2], dtype=bool)
        m[padh[0]: rgb.shape[0] - padh[1], padw[0]: rgb.shape[1] - padw[1]] = False
        rgb[m] = np.array(bg, dtype=np.uint8)
    rgb = rgb[::-1]  # north at the top
    src = Image.fromarray(np.ascontiguousarray(rgb), "RGB")
    a, c, f_ = 1.0 / cell_px, x0 - ix0, iy1 - y_top
    if cell_px >= 4:
        out = src.transform((w, h), Image.AFFINE, (a, 0, c, 0, a, f_), resample=Image.NEAREST)
    else:
        ss = 4
        big = src.transform((w * ss, h * ss), Image.AFFINE, (a / ss, 0, c, 0, a / ss, f_), resample=Image.NEAREST)
        out = big.reduce(ss)
    if gap and cell_px >= 20:
        arr = np.array(out)
        gap_col = np.array(GAP, dtype=np.uint8)
        xs = ((np.arange(0, cam.cells_across + 3) - c) * cell_px).astype(int)
        ys = ((np.arange(0, h / cell_px + 3) - f_) * cell_px).astype(int)
        arr[:, xs[(xs >= 0) & (xs < w)]] = gap_col
        arr[ys[(ys >= 0) & (ys < h)], :] = gap_col
        out = Image.fromarray(arr, "RGB")
    if trail and cell_px >= 4:
        draw_trail(out, cam, player.trail(), size)
    if ant:
        ax, ay = player.ant_xy
        draw_ant_marker(out, cam, ax, ay, player.ant_dir, size)
    return out


def draw_trail(img: Image.Image, cam: Camera, positions: np.ndarray, size=(W, H)):
    """Fading blue dots on the last ant positions (60 % -> 0 %), newest brightest."""
    w, h = size
    n = len(positions)
    if n < 2:
        return
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cell_px = w / cam.cells_across
    r = max(1.5, cell_px * 0.18)
    for i, (x, y) in enumerate(positions[:-1]):
        alpha = 0.6 * (i + 1) / n
        px, py = core.cell_to_px(cam, w, h, float(x) + 0.5, float(y) + 0.5)  # cell centre
        d.ellipse([px - r, py - r, px + r, py + r], fill=(*BLUE, int(255 * alpha)))
    img.paste(layer, (0, 0), layer)


def draw_ant_marker(img: Image.Image, cam: Camera, x: int, y: int, d: int, size=(W, H)):
    """Ant: heading chevron when cell >= 60 px, else a glowing square, min 10 px."""
    w, h = size
    cell_px = w / cam.cells_across
    px, py = core.cell_to_px(cam, w, h, x + 0.5, y + 0.5)
    if cell_px >= 60:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(layer)
        r = cell_px * 0.5
        for i, alpha in ((1.3, 50), (1.1, 80)):
            dl.ellipse([px - r * i, py - r * i, px + r * i, py + r * i], fill=(*BLUE, alpha))
        img.paste(layer, (0, 0), layer)
        core.draw_ant(img, cam, x, y, d, BLUE, glow=None, min_px=10)
        return
    side = max(10.0, cell_px)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    r = side / 2
    for i, alpha in ((3.0, 40), (2.2, 70), (1.5, 110)):
        dl.ellipse([px - r * i, py - r * i, px + r * i, py + r * i], fill=(*BLUE, alpha))
    dl.rectangle([px - r, py - r, px + r, py + r], fill=(*BLUE, 255))
    img.paste(layer, (0, 0), layer)


def new_frame(color=BG, size=(W, H)) -> Image.Image:
    return Image.new("RGB", size, color)


def blend_frames(base: Image.Image, top: Image.Image, opacity: float) -> Image.Image:
    """Return base with `top` composited at the given opacity."""
    return Image.blend(base, top, clamp(opacity))


# --------------------------------------------------------------------------
# Camera helpers (STORYBOARD 2.5, 2.6)
# --------------------------------------------------------------------------

def cam_static(cx: float, cy: float, cells_across: float) -> Camera:
    return Camera(float(cx), float(cy), float(cells_across))


def cam_follow(player: AgePlayer, cells_across: float) -> Camera:
    """Camera locked on the ant (centre of its cell)."""
    x, y = player.ant_xy
    return Camera(x + 0.5, y + 0.5, float(cells_across))


def cam_anchor(cell_xy, screen_xy, cells_across: float) -> Camera:
    """Camera of `cells_across` cells whose cell point `cell_xy` lands on screen point `screen_xy`
    (the inverse of core.cell_to_px); used to keep a subject inside a text-free region."""
    cell_px = W / cells_across
    cx = cell_xy[0] - (screen_xy[0] - W / 2) / cell_px
    cy = cell_xy[1] + (screen_xy[1] - H / 2) / cell_px
    return Camera(float(cx), float(cy), float(cells_across))


def cam_tween(a: Camera, b: Camera, u: float, ease=smoothstep) -> Camera:
    """Blend two cameras; cell size interpolates geometrically (feels linear on screen)."""
    e = ease(u)
    ca = math.exp(lerp(math.log(a.cells_across), math.log(b.cells_across), e))
    return Camera(lerp(a.cx, b.cx, e), lerp(a.cy, b.cy, e), ca)


def cam_pullback(ant_xy, blob_cxy) -> Camera:
    """Auto pull-back rule (S07b/S08): centre = midpoint(ant, blob),
    cells_across = clamp(1.25 * (|ant_x - blob_cx| + 60), 108, 1080)."""
    ax, ay = ant_xy
    bx, by = blob_cxy
    ca = clamp(1.25 * (abs(ax - bx) + 60), 108, 1080)
    return Camera((ax + bx) / 2, (ay + by) / 2, ca)


class LagSmoother:
    """Exponential lag (time constant `tau` s) over vectors, deterministic per frame.

    `value(key, frame, f0, target_fn)` replays from frame f0 whenever the state
    for `key` is not at frame-1, so partial renders (--frames) give the same
    result as a full render.
    """

    def __init__(self, tau: float = 0.3):
        self.tau = tau
        self.state: dict[str, tuple[int, np.ndarray]] = {}
        self.alpha = 1.0 - math.exp(-1.0 / (FPS * tau))

    def value(self, key: str, frame: int, f0: int, target_fn) -> np.ndarray:
        st = self.state.get(key)
        if st is None or st[0] != frame - 1 or frame <= f0:
            v = np.asarray(target_fn(f0), dtype=np.float64)
            for f in range(f0 + 1, frame + 1):
                v = v + (np.asarray(target_fn(f), dtype=np.float64) - v) * self.alpha
        else:
            v = st[1] + (np.asarray(target_fn(frame), dtype=np.float64) - st[1]) * self.alpha
        self.state[key] = (frame, v)
        return v


# --------------------------------------------------------------------------
# Text and UI helpers (STORYBOARD 2.2, 2.4, 2.6)
# --------------------------------------------------------------------------

SHRINK_LOG: list[str] = []
_fit_cache: dict = {}


def measure(text: str, role: str, size: int) -> float:
    return core.font(role, size).getlength(text)


def fit_font(role: str, size: int, text: str, max_w: int = MAX_TEXT_W) -> tuple[ImageFont.FreeTypeFont, int]:
    """Measurement pass: shrink by 4 px steps until the line fits max_w; log shrinks."""
    key = (role, size, text, max_w)
    if key in _fit_cache:
        return _fit_cache[key]
    s = size
    while s > 8 and measure(text, role, s) > max_w:
        s -= 4
    if s != size:
        msg = f"shrink: {role} {size}->{s} px for {text!r} ({measure(text, role, size):.0f} px > {max_w})"
        SHRINK_LOG.append(msg)
        print("[text] " + msg)
    res = (core.font(role, s), s)
    _fit_cache[key] = res
    return res


@dataclass
class Line:
    """One line of a card. `spans` colours whole words, e.g. {"RIGHT": AMBER}."""

    text: str
    role: str = "regular"     # 'bold' | 'regular' | 'mono'
    size: int = 56
    color: tuple = CREAM
    spans: dict = field(default_factory=dict)
    gap_before: int = 0       # extra px above this line


def card_anim(t: float, t0: float, t1: float, snap_in: bool = False, snap_out: bool = False) -> tuple[float, float]:
    """(opacity, dy) of a card living on [t0, t1): 150 ms fades, 12 px upward drift on the way in.
    Hero slams use snap_in=True (1-frame snap, no fade).  The fade-in is offset by one frame so
    the card is already visible (22 %) on its listed frame instead of spending it at opacity 0;
    the fade-out mirrors that (22 % on the last frame), so back-to-back cards always overlap."""
    if t < t0 or t >= t1:
        return 0.0, 0.0
    fin = 0.0 if snap_in else TEXT_FADE
    fout = 0.0 if snap_out else TEXT_FADE
    a = clamp((t - t0 + 1.0 / FPS) / fin) if fin > 0 else 1.0
    b = clamp((t1 - t) / fout) if fout > 0 else 1.0
    return min(a, b), TEXT_DRIFT * (1.0 - a)


def _segments(line: Line) -> list[tuple[str, tuple]]:
    if not line.spans:
        return [(line.text, line.color)]
    segs, buf = [], ""
    for tok in re.split(r"(\s+)", line.text):
        if tok in line.spans:
            if buf:
                segs.append((buf, line.color))
                buf = ""
            segs.append((tok, line.spans[tok]))
        else:
            buf += tok
    if buf:
        segs.append((buf, line.color))
    return segs


def draw_card(
    img: Image.Image,
    lines: list[Line],
    *,
    top: float | None = None,
    center_y: float | None = None,
    cx: float = SAFE_CX,
    x_left: float | None = None,
    opacity: float = 1.0,
    dy: float = 0.0,
    band: bool = True,
    align: str = "center",
) -> tuple[float, float, float, float] | None:
    """Draw a text card (optionally on the 85 % #0B0D12 band, radius 24, pad 28).

    Position with `top` (band top y) or `center_y` (band centre); horizontally
    centred on cx (align='center') or left-aligned at x_left (align='left').
    Every line goes through fit_font (<= 880 px).  Returns the band box.
    """
    if opacity <= 0 or not lines:
        return None
    fonts, widths, heights = [], [], []
    for ln in lines:
        fnt, _ = fit_font(ln.role, ln.size, ln.text)
        asc, desc = fnt.getmetrics()
        fonts.append(fnt)
        widths.append(fnt.getlength(ln.text))
        heights.append((asc + desc) * LINE_SPACING)
    total_h = sum(heights) + sum(ln.gap_before for ln in lines)
    bw = max(widths) + 2 * BAND_PAD
    bh = total_h + 2 * BAND_PAD
    if align == "left":
        bx0 = (x_left if x_left is not None else SAFE_X0 + 20) - BAND_PAD
    else:
        bx0 = cx - bw / 2
    if top is None:
        top = (center_y if center_y is not None else H / 2) - bh / 2
    by0 = top + dy
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * clamp(opacity))
    if band:
        d.rounded_rectangle([bx0, by0, bx0 + bw, by0 + bh], radius=BAND_RADIUS, fill=(*PLAIN, int(BAND_ALPHA * a)))
    y = by0 + BAND_PAD
    for ln, fnt, wdt, hgt in zip(lines, fonts, widths, heights):
        y += ln.gap_before
        x = (bx0 + BAND_PAD) if align == "left" else (cx - wdt / 2)
        asc, desc = fnt.getmetrics()
        ty = y + ((hgt - (asc + desc)) / 2)
        for seg, col in _segments(ln):
            d.text((x, ty), seg, font=fnt, fill=(*col, a))
            x += fnt.getlength(seg)
        y += hgt
    img.paste(layer, (0, 0), layer)
    return (bx0, by0, bx0 + bw, by0 + bh)


PILL_KINDS = {"PROVEN": (GREEN, PLAIN), "UNPROVEN": (AMBER, PLAIN), "OPEN": (AMBER, PLAIN)}


def draw_pill(img: Image.Image, kind: str, x: float, y: float, opacity: float = 1.0) -> tuple[float, float, float, float]:
    """PROVEN (green) / UNPROVEN, OPEN (amber) pill: Bold 56 on a radius-28 rect, pad 20 x 8.
    (x, y) is the top-left corner.  Returns the pill box."""
    fill, tcol = PILL_KINDS[kind]
    fnt, _ = fit_font("bold", 56, kind)
    asc, desc = fnt.getmetrics()
    tw, th = fnt.getlength(kind), asc + desc
    box = (x, y, x + tw + 40, y + th + 16)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * clamp(opacity))
    d.rounded_rectangle(box, radius=28, fill=(*fill, a))
    d.text((x + 20, y + 8), kind, font=fnt, fill=(*tcol, a))
    img.paste(layer, (0, 0), layer)
    return box


def draw_pill_card(img: Image.Image, kind: str, lines: list[Line], *, top: float, opacity: float = 1.0,
                   dy: float = 0.0, x: float = 100) -> tuple[tuple, tuple] | None:
    """Band spanning the safe width (x 80..960, centred on 520) with a pill at `x` above
    left-aligned lines (2.6: the pill sits 'left of or above' the line; side by side the pill
    plus a 700 px line would exceed 880 px).  Returns (band box, text card box)."""
    if opacity <= 0:
        return None
    pill_h = sum(core.font("bold", 56).getmetrics()) + 16
    text_h = 0.0
    for ln in lines:
        fnt, _ = fit_font(ln.role, ln.size, ln.text)
        text_h += sum(fnt.getmetrics()) * LINE_SPACING + ln.gap_before
    gap = 12
    bh = BAND_PAD + pill_h + gap + text_h + BAND_PAD
    y0 = top + dy
    band = (SAFE_X0, y0, SAFE_X1, y0 + bh)
    core.draw_rect(img, list(band), PLAIN, BAND_ALPHA * opacity, radius=BAND_RADIUS)
    draw_pill(img, kind, x, y0 + BAND_PAD, opacity)
    text = draw_card(img, lines, top=y0 + pill_h + gap, x_left=x, align="left", opacity=opacity, band=False)
    return band, text


def draw_counter(
    img: Image.Image,
    step: int,
    *,
    x: float = 100,
    y: float = 1520,
    size: int = 60,
    running: bool = True,
    prefix: str = "step ",
    suffix: str = "",
    opacity: float = 1.0,
    band: bool = True,
) -> tuple[float, float, float, float] | None:
    """Mono counter: amber while running, cream when frozen; thousands separators.

    (x, y) = left edge and vertical CENTRE of the text line; the compact band
    (pad 14, radius 16) extends ~14 px beyond the glyph box on each side."""
    if opacity <= 0:
        return None
    text = f"{prefix}{fmt_int(step)}{suffix}"
    fnt, _ = fit_font("mono", size, text)
    asc, desc = fnt.getmetrics()
    tw, th = fnt.getlength(text), asc + desc
    pad = 14
    box = (x - pad, y - th / 2 - pad, x + tw + pad, y + th / 2 + pad)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * clamp(opacity))
    if band:
        d.rounded_rectangle(box, radius=16, fill=(*PLAIN, int(BAND_ALPHA * a)))
    d.text((x, y - th / 2), text, font=fnt, fill=(*(AMBER if running else CREAM), a))
    img.paste(layer, (0, 0), layer)
    return box


def draw_turn_strip(
    img: Image.Image,
    turns: np.ndarray,
    end_step: int,
    *,
    x0: int = 100, x1: int = 932, y0: int = 1440, y1: int = 1500,
    n_ticks: int = 208, bracket: int = 104, label: str = "104 turns",
    opacity: float = 1.0, first_step: int = 0,
):
    """Barcode of the last `n_ticks` turns up to `end_step`: R = tick up (amber),
    L = tick down (cream), 4 px per tick; an amber bracket under the last `bracket`
    ticks with a label and a loop arrow (STORYBOARD S07).  Occupies y0-8 .. y1+48.
    Turns before `first_step` (the onset) are never drawn: the barcode shows only the
    periodic regime, so its ticks are pixel-identical from the first full window on."""
    if opacity <= 0:
        return
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * clamp(opacity))
    tick_w = (x1 - x0) / n_ticks
    mid = (y0 + y1) / 2
    s0 = max(0, first_step, end_step - n_ticks)
    seg = turns[s0:end_step]
    d.rounded_rectangle([x0 - 12, y0 - 8, x1 + 12, y1 + 8], radius=12, fill=(*PLAIN, int(BAND_ALPHA * a)))
    for i, tv in enumerate(seg):
        px = x0 + (n_ticks - len(seg) + i) * tick_w
        if tv == 1:
            d.rectangle([px, y0, px + tick_w - 1, mid], fill=(*AMBER, a))
        else:
            d.rectangle([px, mid, px + tick_w - 1, y1], fill=(*CREAM, a))
    bx0 = x1 - bracket * tick_w
    by = y1 + 14
    d.line([(bx0, by - 8), (bx0, by), (x1, by), (x1, by - 8)], fill=(*AMBER, a), width=3, joint="curve")
    # loop arrow beneath the bracket: from the right end back to the bracket start
    ay = by + 22
    d.arc([bx0, ay - 18, x1, ay + 18], start=0, end=180, fill=(*AMBER, a), width=3)
    d.polygon([(bx0 - 9, ay + 2), (bx0 + 9, ay + 2), (bx0, ay - 10)], fill=(*AMBER, a))
    fnt, _ = fit_font("mono", 44, label)
    lw, lh = fnt.getlength(label), sum(fnt.getmetrics())
    d.text((bx0 - 20 - lw, by + 4), label, font=fnt, fill=(*AMBER, a))
    img.paste(layer, (0, 0), layer)


def draw_bar_chart(
    img: Image.Image,
    bins: list[dict],
    *,
    box: tuple = (100, 1240, 940, 1560),
    markers: list = (),
    title: str | None = None,
    opacity: float = 1.0,
    label_size: int = 36,
):
    """Log-x histogram of `bins` ([{lo, hi, count}, ...]) in cream bars.

    markers: [(value, label, color), ...] drawn as vertical lines with a label.
    Axis labels use Mono `label_size` (>= 36) in the secondary colour.
    """
    if opacity <= 0 or not bins:
        return
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * clamp(opacity))
    d.rounded_rectangle([x0, y0, x1, y1], radius=BAND_RADIUS, fill=(*PLAIN, int(BAND_ALPHA * a)))
    fnt = core.font("mono", label_size)
    pad = 24
    title_h = (sum(fnt.getmetrics()) + 8) if title else 0
    axis_h = sum(fnt.getmetrics()) + 8
    px0, px1 = x0 + pad, x1 - pad
    py0, py1 = y0 + pad + title_h, y1 - pad - axis_h
    lo_all = math.log10(max(1, min([bins[0]["lo"]] + [m[0] for m in markers])))
    hi_all = math.log10(max(2, max([bins[-1]["hi"]] + [m[0] * 1.15 for m in markers])))

    def xpos(v):
        return px0 + (math.log10(max(1, v)) - lo_all) / (hi_all - lo_all) * (px1 - px0)

    cmax = max(1, max(b["count"] for b in bins))
    for b in bins:
        bx0, bx1 = xpos(b["lo"]), xpos(b["hi"])
        hgt = (py1 - py0) * (math.log10(1 + b["count"]) / math.log10(1 + cmax))
        d.rectangle([bx0 + 1, py1 - hgt, bx1 - 1, py1], fill=(*CREAM, a))
    if title:
        tf, _ = fit_font("mono", label_size, title, max_w=px1 - px0)
        d.text((px0, y0 + pad - 4), title, font=tf, fill=(*SECONDARY, a))
    last_label_right = -1e9
    for v in (100, 1000, 10000, 100000, 1000000):
        if lo_all <= math.log10(v) <= hi_all:
            xv = xpos(v)
            d.line([(xv, py1), (xv, py1 + 6)], fill=(*SECONDARY, a), width=2)
            lab = fmt_int(v)
            lw = fnt.getlength(lab)
            # the label is centred on its tick but never leaves the chart box (STORYBOARD 2.3);
            # a label that would then collide with its neighbour is dropped (the tick stays)
            lx = clamp(xv - lw / 2, x0 + 8, x1 - 8 - lw)
            if lx < last_label_right + 12:
                continue
            d.text((lx, py1 + 8), lab, font=fnt, fill=(*SECONDARY, a))
            last_label_right = lx + lw
    lh = sum(fnt.getmetrics())
    for i, (value, label, color) in enumerate(markers):
        xv = xpos(value)
        d.line([(xv, py0), (xv, py1)], fill=(*PLAIN, a), width=7)   # dark halo so the line reads over cream bars
        d.line([(xv, py0), (xv, py1)], fill=(*color, a), width=3)
        lw = fnt.getlength(label)
        lx = xv + 8 if xv + 8 + lw <= px1 else xv - 8 - lw
        ly = py0 + i * lh
        d.rounded_rectangle([lx - 6, ly, lx + lw + 6, ly + lh], radius=8, fill=(*PLAIN, int(BAND_ALPHA * a)))  # legible over the bars
        d.text((lx, ly), label, font=fnt, fill=(*color, a))
    img.paste(layer, (0, 0), layer)


def draw_dot_wall(
    img: Image.Image,
    status: np.ndarray,
    n_filled: int,
    *,
    box: tuple = (136, 470, 904, 1238),
    dot: int = 3,
    opacity: float = 1.0,
    flash: float = 0.0,
):
    """256 x 256 wall of `dot` px dots, one per 4x4 pattern (index = config index, row-major).
    Dots with index < n_filled are amber (red if status != 0); the rest stay dark.
    `flash` (0..1) whitens the whole wall (4 % white flash at completion)."""
    if opacity <= 0:
        return
    side = int(round(math.sqrt(len(status))))
    n_filled = int(clamp(n_filled, 0, len(status)))
    cls = np.zeros(len(status), dtype=np.uint8)           # 0 dark, 1 amber, 2 red
    cls[:n_filled] = 1
    cls[:n_filled][status[:n_filled] != 0] = 2
    lut = np.array([GAP, AMBER, RED], dtype=np.float32)
    rgb = lut[cls].reshape(side, side, 3)
    if flash > 0:
        rgb = rgb * (1 - flash) + 255.0 * flash
    tile = Image.fromarray(rgb.astype(np.uint8), "RGB").resize((side * dot, side * dot), Image.NEAREST)
    x0, y0 = box[0], box[1]
    if opacity >= 1.0:
        img.paste(tile, (int(x0), int(y0)))
    else:
        base = img.crop((int(x0), int(y0), int(x0) + tile.width, int(y0) + tile.height))
        img.paste(Image.blend(base, tile, opacity), (int(x0), int(y0)))


def draw_safe_zone(img: Image.Image):
    """Debug overlay: the text safe zone rectangle (STORYBOARD 2.3)."""
    d = ImageDraw.Draw(img)
    d.rectangle([SAFE_X0, SAFE_Y0, SAFE_X1, SAFE_Y1], outline=RED, width=2)
    d.line([(SAFE_CX, SAFE_Y0), (SAFE_CX, SAFE_Y1)], fill=RED, width=1)


# --------------------------------------------------------------------------
# Audio-state helper (see SCENES_CONTRACT.md)
# --------------------------------------------------------------------------

def audio_state(*, osc=None, pad=None, drone=None, mute=False, noise=None) -> dict:
    """Build a per-frame audio state with the contract's defaults filled in.

    osc:   list of {"run": id, "step": int, "gain_db": float} (or a single dict)
    pad:   {"chord": name-or-list, "cutoff": Hz, "detune_cents": c, "gain_db": g} or None
    drone: {"on": bool, "gain_db": -24, "add_e": bool}
    noise: {"gain_db": g, "cutoff": Hz} or None (S11 shimmer)
    """
    if osc is None:
        osc = []
    elif isinstance(osc, dict):
        osc = [osc]
    voices = []
    for v in osc:
        voices.append({"run": v["run"], "step": int(v["step"]), "gain_db": float(v.get("gain_db", -16.0))})
    d = {"on": True, "gain_db": -24.0, "add_e": False}
    if drone is not None:
        d.update(drone)
    p = None
    if pad is not None:
        p = {"chord": pad.get("chord", "highway"), "cutoff": float(pad.get("cutoff", 1200.0)),
             "detune_cents": float(pad.get("detune_cents", 0.0)), "gain_db": float(pad.get("gain_db", -20.0))}
    return {"osc": voices, "pad": p, "drone": d, "mute": bool(mute), "noise": noise}
