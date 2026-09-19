"""Evidence chapter scenes: S09-S14 (STORYBOARD 3.2, sections 2, 3.3, 4.4).

S09 THE MYSTERY        plain background + the S08 road at 20 %, a re-rolling 4x4 start box
S10 MOSAIC             six live runs from the six real 4x4 patterns of STORYBOARD 3.3
S11 THE COUNT          the 256 x 256 dot wall of every 4x4 start, counter and side bars
S12 THE STUBBORNEST    the longest-delay run played live, real 4x4 onset histogram
S13 VERDICT            tested / highways / exceptions, "That's evidence. Not a proof."
S14 SCORECARD          PROVEN / PROVEN / UNPROVEN over the running highway at 25 %

Every number on screen comes from ctx.facts (SCENES_CONTRACT 3.1); the runs come
from ctx.runs; audio directives follow SCENES_CONTRACT 4.  All scene functions
are pure per frame (per-frame smoothing only through ctx.lag).
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

import core
from core import Camera, clamp, lerp, smoothstep
import common
from common import (
    AMBER, BG, CREAM, GAP, PLAIN, RED, SECONDARY, SAFE_CX, W, H, FPS,
    BAND_ALPHA, LINE_SPACING, Line, audio_state, card_anim, fmt_int, frame_of,
)

HOLD = 1e9                 # card end time "hold to the hard cut" (no fade-out)
PAD_FULL_DB = -20.0        # pad level for full chords
PAD_THIN_DB = -24.0        # pad level for thin chords (lone A2)
_cache: dict = {}          # per-ctx derived values, keyed by (id(ctx), name)


def _memo(ctx, name: str, fn):
    key = (id(ctx), name)
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]


# --------------------------------------------------------------------------
# Private drawing helpers
# --------------------------------------------------------------------------

def _text_band(img, text, role, size, color, *, y_center, x=None, cx=None, opacity=1.0,
               dx=0.0, band_h=None, pad=14, band=True):
    """One line of text on a compact band (pad 14, radius 16), like draw_counter.

    Positioned by its left edge `x` or centre `cx`; `y_center` is the vertical
    centre of the text.  `band_h` forces the band height (side bars = 60 px).
    Returns the band box."""
    if opacity <= 0:
        return None
    fnt, _ = common.fit_font(role, size, text)
    asc, desc = fnt.getmetrics()
    tw, th = fnt.getlength(text), asc + desc
    if x is None:
        x = cx - tw / 2
    x += dx
    hh = (band_h / 2) if band_h else (th / 2 + pad)
    box = (x - pad, y_center - hh, x + tw + pad, y_center + hh)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * clamp(opacity))
    if band:
        d.rounded_rectangle(box, radius=16, fill=(*PLAIN, int(BAND_ALPHA * a)))
    d.text((x, y_center - th / 2), text, font=fnt, fill=(*color, a))
    img.paste(layer, (0, 0), layer)
    return box


def _zero_padded(n: int, width_of: int) -> str:
    """fmt_int with leading zeros to the digit count of `width_of`: 0 -> '00,000'."""
    digits = len(str(int(width_of)))
    s = f"{int(n):0{digits}d}"
    groups = []
    while s:
        groups.insert(0, s[-3:])
        s = s[:-3]
    return ",".join(groups)


def _underline(img, x0, x1, y, opacity, color=AMBER, width=4):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).line([(x0, y), (x1, y)], fill=(*color, int(255 * clamp(opacity))), width=width)
    img.paste(layer, (0, 0), layer)


def _random_max_k(facts) -> int:
    """Largest random box size (S11 side bar 'random, up to KxK:'); never guessed."""
    rnd = facts.random
    if "max_k" in rnd:
        return int(rnd["max_k"])
    if "k_values" in rnd:
        return int(max(rnd["k_values"]))
    raise common.FactsError("movie_facts: missing required field 'random.max_k'")


# --------------------------------------------------------------------------
# S09 THE MYSTERY (33.0-38.0)
# --------------------------------------------------------------------------

S09_BOX_CXY = (520, 900)     # screen centre of the 4x4 box
S09_CELL_PX = 80
S09_BOX_T0, S09_ROLL_DT, S09_N_ROLLS = 35.5, 0.3, 6   # appears, re-rolls 6 times, locks on the 7th
S09_SEED = 20260919


def _s09_patterns() -> np.ndarray:
    """(7, 4, 4) uint8 patterns: real random bits, seeded; [i, row (north first), col (west first)]."""
    rng = np.random.default_rng(S09_SEED)
    return rng.integers(0, 2, size=(S09_N_ROLLS + 1, 4, 4), dtype=np.uint8)


def _s09_roll_frames() -> list[int]:
    return [frame_of(S09_BOX_T0 + S09_ROLL_DT * i) for i in range(S09_N_ROLLS + 1)]


def _draw_start_box(img, pattern: np.ndarray, locked: bool, opacity: float):
    """A 4x4 start box (cells -2..1, CONVENTIONS even-k box) at 80 px/cell, ant at the
    origin cell facing N; marked cells cream, hairline gaps, amber outline once locked."""
    if opacity <= 0:
        return
    k = pattern.shape[0]
    px = S09_CELL_PX
    cx, cy = S09_BOX_CXY
    x0, y0 = cx - k * px / 2, cy - k * px / 2
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * clamp(opacity))
    d.rectangle([x0, y0, x0 + k * px, y0 + k * px], fill=(*BG, a))
    for r in range(k):
        for c in range(k):
            if pattern[r, c]:
                d.rectangle([x0 + c * px, y0 + r * px, x0 + (c + 1) * px - 1, y0 + (r + 1) * px - 1], fill=(*CREAM, a))
    for i in range(k + 1):
        d.line([(x0 + i * px, y0), (x0 + i * px, y0 + k * px)], fill=(*GAP, a), width=1)
        d.line([(x0, y0 + i * px), (x0 + k * px, y0 + i * px)], fill=(*GAP, a), width=1)
    outline = (*AMBER, a) if locked else (*SECONDARY, a // 2)
    d.rounded_rectangle([x0 - 4, y0 - 4, x0 + k * px + 4, y0 + k * px + 4], radius=6, outline=outline, width=3)
    img.paste(layer, (0, 0), layer)
    # ant at the origin cell facing N: a camera whose cell (0, 0) lands on the box's origin cell
    cam = Camera(cx=(W / 2 - cx) / px, cy=(cy - H / 2) / px, cells_across=W / px)
    with_ant = img.copy()
    common.draw_ant_marker(with_ant, cam, 0, 0, 0)
    img.paste(Image.blend(img, with_ant, clamp(opacity)))


def S09(ctx, t_local, frame):
    t = ctx.t
    img = common.blend_frames(common.new_frame(PLAIN), ctx.road_backdrop(989), 0.20)
    op, dy = card_anim(t, 33.0, 35.5)
    common.draw_card(img, [Line("Nobody can", "bold", 84), Line("prove why.", "bold", 84)],
                     center_y=800, opacity=op, dy=dy, band=False)
    rolls = _s09_roll_frames()
    if frame >= rolls[0]:
        idx = sum(1 for rf in rolls if frame >= rf) - 1
        op_box, _ = card_anim(t, S09_BOX_T0, HOLD)
        _draw_start_box(img, _s09_patterns()[idx], locked=idx == S09_N_ROLLS, opacity=op_box)
    op, dy = card_anim(t, 35.5, HOLD)
    common.draw_card(img, [Line("Change the start.", "regular", 56), Line("Any finite start you like.", "regular", 56)],
                     top=300, opacity=op, dy=dy)
    events = []
    for i, rf in enumerate(rolls[1:], start=1):
        if frame == rf:
            events.append({"type": "click_cluster"})
            if i == S09_N_ROLLS:
                events.append({"type": "knock"})
    state = audio_state(osc=[], pad={"chord": "lone_a2", "cutoff": 800.0, "gain_db": PAD_THIN_DB})
    return img, state, events


# --------------------------------------------------------------------------
# S10 MOSAIC (38.0-44.0)
# --------------------------------------------------------------------------

TILE_X = (140, 580)
TILE_Y = (384, 784, 1184)      # storyboard 360/760/1160 + 24: the card band (top 250) ends at ~376
TILE_PX = 360
TILE_CELLS = 100
S10_STEPS_PER_FRAME = 6000 // FPS       # 6,000 steps/s
BLIP_NOTES = ("A4", "B4", "C#5", "E5", "F#5", "A5")


def _tile_start_frame(ctx, i: int) -> int:
    return ctx.shot.f0 + frame_of(float(ctx.facts.mosaic_tiles[i]["delay"]))


def _tile_step(ctx, i: int, frame: int) -> int:
    n = len(ctx.runs.turns(f"mosaic{i}"))
    return int(min(n, max(0, frame - _tile_start_frame(ctx, i)) * S10_STEPS_PER_FRAME))


def _tile_road_sign(ctx, i: int) -> tuple[int, int]:
    """(sx, sy) of tile i's highway displacement, derived from the run itself (the direction the
    road exits the tile; screen: sx > 0 = right, sy > 0 = up)."""
    def derive():
        run, onset = ctx.runs.run(f"mosaic{i}"), ctx.runs.onset(f"mosaic{i}")
        sx, sy = np.sign(run.pos[onset + ctx.facts.period] - run.pos[onset])
        return int(sx), int(sy)
    return _memo(ctx, f"sign{i}", derive)


def _tile_cert_step(ctx, i: int) -> int:
    """Certification step of tile i, re-derived from the run (CONVENTIONS: 20 exact periods
    after onset AND the ant >= 20 cells beyond the pre-onset bbox in both coordinates)."""
    def derive():
        rid = f"mosaic{i}"
        run, stats, onset = ctx.runs.run(rid), ctx.runs.stats(rid), ctx.runs.onset(rid)
        period = ctx.facts.period
        bx0, by0, bx1, by1 = stats.bbox_at(onset)
        sx, sy = _tile_road_sign(ctx, i)
        p = run.pos[onset:]
        okx = (p[:, 0] >= bx1 + 20) if sx > 0 else (p[:, 0] <= bx0 - 20)
        oky = (p[:, 1] >= by1 + 20) if sy > 0 else (p[:, 1] <= by0 - 20)
        hit = np.nonzero(okx & oky)[0]
        if not len(hit):
            raise common.FactsError(f"mosaic tile {i}: the ant never escapes its blob by 20 cells")
        return max(onset + 21 * period, onset + int(hit[0]))
    return _memo(ctx, f"cert{i}", derive)


def _tile_cert_frame(ctx, i: int) -> int:
    return _tile_start_frame(ctx, i) + int(math.ceil(_tile_cert_step(ctx, i) / S10_STEPS_PER_FRAME))


def _draw_tile(ctx, img, i: int, frame: int):
    tile = ctx.facts.mosaic_tiles[i]
    rid = f"mosaic{i}"
    player, stats, onset = ctx.runs.player(rid), ctx.runs.stats(rid), ctx.runs.onset(rid)
    step = _tile_step(ctx, i, frame)
    player.seek(step)
    started = frame > _tile_start_frame(ctx, i)
    cx, cy = ctx.lag.value(f"s10_c{i}", frame, ctx.shot.f0,
                           lambda f: stats.centroid_at(min(_tile_step(ctx, i, f), onset)))
    cam = Camera(float(cx), float(cy), float(TILE_CELLS))
    pic = common.render_run(player, cam, size=(TILE_PX, TILE_PX),
                            steps_drawn=S10_STEPS_PER_FRAME if started else 0, visited=False, trail=False)
    x0, y0 = TILE_X[tile["col"] - 1], TILE_Y[tile["row"] - 1]
    img.paste(pic, (x0, y0))
    certified = step >= _tile_cert_step(ctx, i)
    d = ImageDraw.Draw(img)
    d.rectangle([x0 - 2, y0 - 2, x0 + TILE_PX + 1, y0 + TILE_PX + 1], outline=AMBER if certified else GAP, width=3)
    if certified:
        op, dy = card_anim(ctx.t, _tile_cert_frame(ctx, i) / FPS, HOLD)
        lines = [Line("road at", "mono", 40, AMBER), Line(f"step {fmt_int(onset)}", "mono", 40, AMBER)]
        _draw_tile_label(img, lines, (x0, y0), _tile_road_sign(ctx, i), op, dy)


def _draw_tile_label(img, lines, tile_xy, road_sign, opacity, dy):
    """Two-line mono label on a compact band (pad 12) inside a tile, kept off the road: the
    road leaves the (centred) blob toward the corner given by `road_sign`, so the label sits
    at the tile's top edge when the road exits downward (else the bottom edge), pushed toward
    the side opposite the road's x direction."""
    if opacity <= 0:
        return
    fonts = [common.fit_font(ln.role, ln.size, ln.text)[0] for ln in lines]
    bw = max(f.getlength(ln.text) for f, ln in zip(fonts, lines)) + 2 * 12
    bh = sum(sum(f.getmetrics()) * LINE_SPACING for f in fonts) + 2 * 12
    sx, sy = road_sign
    cx = tile_xy[0] + TILE_PX / 2 - sx * ((TILE_PX - bw) / 2 - 8)
    cy = tile_xy[1] + (8 + bh / 2 if sy < 0 else TILE_PX - 8 - bh / 2) + dy
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * clamp(opacity))
    d.rounded_rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], radius=16, fill=(*PLAIN, int(BAND_ALPHA * a)))
    y = cy - bh / 2 + 12
    for ln, f in zip(lines, fonts):
        asc, desc = f.getmetrics()
        hgt = (asc + desc) * LINE_SPACING
        d.text((cx - f.getlength(ln.text) / 2, y + (hgt - asc - desc) / 2), ln.text, font=f, fill=(*ln.color, a))
        y += hgt
    img.paste(layer, (0, 0), layer)


def S10(ctx, t_local, frame):
    t = ctx.t
    img = common.new_frame(BG)
    n_tiles = len(ctx.facts.mosaic_tiles)
    for i in range(n_tiles):
        _draw_tile(ctx, img, i, frame)
    op, dy = card_anim(t, 38.0, 41.0)
    common.draw_card(img, [Line("Every one we tried builds a road.", "regular", 52)], top=250, opacity=op, dy=dy)
    op, dy = card_anim(t, 41.0, HOLD)
    common.draw_card(img, [Line("Nobody can prove it always will.", "regular", 52)], top=250, opacity=op, dy=dy)
    # audio: one crackle voice per running tile, blips ascending in certification order
    voices = [{"run": f"mosaic{i}", "step": _tile_step(ctx, i, frame), "gain_db": -26.0}
              for i in range(n_tiles) if frame > _tile_start_frame(ctx, i)]
    order = _memo(ctx, "cert_order", lambda: sorted(range(n_tiles), key=lambda i: _tile_cert_frame(ctx, i)))
    events = [{"type": "blip", "note": BLIP_NOTES[rank]} for rank, i in enumerate(order) if frame == _tile_cert_frame(ctx, i)]
    pad = ({"chord": "highway", "cutoff": 1200.0, "gain_db": PAD_FULL_DB} if t < 41.0
           else {"chord": "lone_a2", "cutoff": 800.0, "gain_db": PAD_THIN_DB})
    return img, audio_state(osc=voices, pad=pad), events


# --------------------------------------------------------------------------
# S11 THE COUNT (44.0-50.0)
# --------------------------------------------------------------------------

WALL_BOX = (136, 470, 904, 1238)
S11_T_DONE = 47.5
S11_RATE0, S11_RATE1 = 1.0, 2000.0        # dots per frame, start -> end of the fill
S11_COUNTER_TOP = 390                      # text top of the 'tested' counter (plain background, no band)
S11_BAR_X = 136                            # left edge of the side bars (60 px rows, plain background)
S11_BAR_Y = (1290, 1360, 1430, 1500)       # 60 px rows; the random bar takes two rows
S11_BAR_T = (48.0, 48.25, 48.5)            # 3x3 bar, random bar, 5x5 bar slide in
S11_TICK_LIMIT = 200 / FPS                 # dots/frame above which the shimmer takes over


def _s11_fill(ctx) -> np.ndarray:
    """n_filled per local frame: cumulative dots, rate 1 -> 2,000 per frame (power ramp
    solved so the wall completes exactly on the 47.5 s frame)."""
    def build():
        n_total = len(ctx.k4["status"])
        if n_total != ctx.facts.n4:
            raise common.FactsError(f"k4 records hold {n_total} patterns, facts say n4 = {ctx.facts.n4}")
        nf = frame_of(S11_T_DONE) - ctx.shot.f0          # 105 frames of filling
        u = np.arange(nf) / (nf - 1)
        lo, hi = 0.01, 20.0
        for _ in range(100):                             # bisection on the ramp exponent
            p = 0.5 * (lo + hi)
            total = np.sum(S11_RATE0 + (S11_RATE1 - S11_RATE0) * u ** p)
            lo, hi = (p, hi) if total > n_total else (lo, p)
        rate = S11_RATE0 + (S11_RATE1 - S11_RATE0) * u ** (0.5 * (lo + hi))
        cum = np.concatenate([[0], np.round(np.cumsum(rate))]).astype(np.int64)
        cum[-1] = n_total
        return np.minimum(cum, n_total)
    return _memo(ctx, "s11_fill", build)


def _s11_n_filled(ctx, frame: int) -> int:
    fill = _s11_fill(ctx)
    return int(fill[int(clamp(frame - ctx.shot.f0, 0, len(fill) - 1))])


def _s11_side_bars(ctx) -> list[list[tuple[str, int]]]:
    """Side bars in display order, each a list of (text, mono size) rows (STORYBOARD S11 /
    section 6): the random bar is the storyboard's two Mono 40 fragments on two rows."""
    f = ctx.facts
    bars = []
    e3 = f.exh(3)
    if e3 is not None:
        bars.append([(f"3x3 box: {fmt_int(e3['n_highway'])} / {fmt_int(e3['n_configs'])}", 40)])
    mk = _random_max_k(f)
    bars.append([(f"random, up to {mk}x{mk}:", 40),
                 (f"{fmt_int(f.random['total_highway'])} / {fmt_int(f.random['total_tested'])}", 40)])
    if f.show_k5:
        e5 = f.exh(5)
        bars.append([(f"5x5 box: {fmt_int(e5['n_highway'])} / {fmt_int(e5['n_configs'])}", 36)])
    return bars


def S11(ctx, t_local, frame):
    t = ctx.t
    f = ctx.facts
    img = common.new_frame(PLAIN)
    n4, n4h = f.n4, f.n4_highway
    status = ctx.k4["status"]
    n_filled = _s11_n_filled(ctx, frame)
    done = frame >= frame_of(S11_T_DONE)
    frames_since_done = frame - frame_of(S11_T_DONE)
    flash = 0.04 * max(0.0, 1.0 - frames_since_done / 3.0) if done else 0.0
    common.draw_dot_wall(img, status, n_filled, box=WALL_BOX, flash=flash)
    counter = f"tested {_zero_padded(n_filled, n4)} / {fmt_int(n4)}"
    th = sum(core.font("mono", 60).getmetrics())
    _text_band(img, counter, "mono", 60, CREAM if done else AMBER, cx=SAFE_CX, y_center=S11_COUNTER_TOP + th / 2, band=False)
    op, dy = card_anim(t, 44.0, S11_T_DONE)
    common.draw_card(img, [Line(f"Every 4x4 start. All {fmt_int(n4)}.", "regular", 56)], top=250, opacity=op, dy=dy)
    result = (f"{fmt_int(n4h)} / {fmt_int(n4)} built the road." if n4h == n4
              else f"{fmt_int(n4h)} / {fmt_int(n4)} certified")
    op, dy = card_anim(t, S11_T_DONE, HOLD, snap_in=True)
    common.draw_card(img, [Line(result, "regular", 52)], top=250, opacity=op, dy=dy)
    events = []
    rows = iter(S11_BAR_Y)
    for bar, t_in in zip(_s11_side_bars(ctx), S11_BAR_T):
        op, _ = card_anim(t, t_in, HOLD)
        for text, size in bar:
            _text_band(img, text, "mono", size, SECONDARY, x=S11_BAR_X, y_center=next(rows) + 30, opacity=op,
                       dx=-40 * (1 - op), band=False)
        if ctx.at(frame, t_in):
            events.append({"type": "slot_click"})
    # audio: micro-ticks per dot, shimmer above 200/s, pad climbing A2 -> C#3 -> E3, chord hit on completion
    dots = n_filled - _s11_n_filled(ctx, frame - 1)
    if dots > 0:
        events.append({"type": "micro_tick", "n": int(dots)})
    if ctx.at(frame, S11_T_DONE):
        events.append({"type": "chord_hit"})
    noise = None
    if dots > S11_TICK_LIMIT:
        u = clamp(math.log(dots / S11_TICK_LIMIT) / math.log(S11_RATE1 / S11_TICK_LIMIT))
        noise = {"gain_db": lerp(-36.0, -24.0, u), "cutoff": lerp(1500.0, 6000.0, u)}
    if done:
        pad = {"chord": "highway", "cutoff": 1200.0, "gain_db": PAD_FULL_DB}
    else:
        stage = int(clamp((t - 44.0) / (S11_T_DONE - 44.0) * 3, 0, 2))
        pad = {"chord": ("climb_a2", "climb_cs3", "climb_e3")[stage], "cutoff": 900.0, "gain_db": PAD_FULL_DB}
    return img, audio_state(osc=[], pad=pad, noise=noise), events


# --------------------------------------------------------------------------
# S12 THE STUBBORNEST START (50.0-57.0)
# --------------------------------------------------------------------------

S12_T_RUN, S12_T_ONSET = 50.6, 55.4        # run starts / onset frame
S12_STATIC_PX = 20                         # px per cell for the static pattern
S12_AUTOFIT_ABOVE = 48                     # auto-fit when the start box is wider than this
S12_CHART_BOX = (100, 1240, 940, 1560)
S12_TWEEN_S = 0.6                          # static -> auto-fit camera hand-off
S12_STAGE_Y = (510, 1125)                  # text-free band: below card B (ends ~502), above the counter band (~1131)
S12_STAGE_CY = sum(S12_STAGE_Y) / 2
S12_POST_STEPS_PER_FRAME = 104             # after the onset: one period per frame, as in S07
S12_TIP_CELLS = 160                        # cells across once the camera has dived to the road tip (57.0)


def _s12_step(ctx, frame: int) -> int:
    """Displayed step of the longest run: constant rate LONGEST_ONSET / 4.8 s from 50.6 s,
    landing exactly on the onset at 55.4 s; then one period per frame to the cut, so the
    fresh road and the ant stay inside the stage band (the counter is frozen by then)."""
    f_run, f_on = frame_of(S12_T_RUN), frame_of(S12_T_ONSET)
    if frame <= f_run:
        return 0
    onset = ctx.facts.longest_onset
    if frame <= f_on:
        return int(round(onset * (frame - f_run) / (f_on - f_run)))
    n = len(ctx.runs.turns("longest"))
    return int(min(n, onset + S12_POST_STEPS_PER_FRAME * (frame - f_on)))


def _s12_fit(bbox) -> Camera:
    """STORYBOARD 2.5 auto-fit of a modified-cell bbox, but into the stage band rather than the
    full frame: cells_across = clamp(1.3 * max(bw, bh * 1080 / stage_h, 64), 64, 1080) and the
    bbox centre lands on the stage centre, so nothing of the run hides under the card, the
    counter or the histogram."""
    x0, y0, x1, y1 = (float(v) for v in bbox)
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    stage_h = S12_STAGE_Y[1] - S12_STAGE_Y[0]
    ca = clamp(1.3 * max(bw, bh * W / stage_h, 64), 64, 1080)
    return common.cam_anchor(((x0 + x1 + 1) / 2, (y0 + y1 + 1) / 2), (W / 2, S12_STAGE_CY), ca)


def _s12_camera(ctx, frame: int) -> Camera:
    """Static stage fit (50.0-50.6) -> lagged auto-fit of the growing bbox (to the onset) ->
    a 1.6 s smoothstep dive that slides the ant from where the fit shows it to the stage centre
    while zooming to S12_TIP_CELLS, so the ant and the fresh road are on screen to the cut."""
    stats = ctx.runs.stats("longest")
    x0, y0, x1, y1 = stats.bbox_at(1)
    if max(x1 - x0 + 1, y1 - y0 + 1) > S12_AUTOFIT_ABOVE:
        static = _s12_fit((x0, y0, x1, y1))
    else:
        static = common.cam_anchor(((x0 + x1 + 1) / 2, (y0 + y1 + 1) / 2), (W / 2, S12_STAGE_CY), W / S12_STATIC_PX)
    if ctx.t < S12_T_RUN:
        return static
    f_on = frame_of(S12_T_ONSET)

    def lagged_fit(f):
        return _s12_fit(ctx.lag.value("s12_bbox", f, ctx.shot.f0, lambda g: stats.bbox_at(max(1, _s12_step(ctx, g)))))

    if frame <= f_on:
        return common.cam_tween(static, lagged_fit(frame), (ctx.t - S12_T_RUN) / S12_TWEEN_S)
    fit = _memo(ctx, "s12_fit_at_onset", lambda: lagged_fit(f_on))
    ax, ay = (float(v) + 0.5 for v in ctx.runs.run("longest").pos[_s12_step(ctx, frame)])
    e = smoothstep((frame - f_on) / (ctx.shot.f1 - 1 - f_on))
    ca = math.exp(lerp(math.log(fit.cells_across), math.log(S12_TIP_CELLS), e))
    hx, hy = core.cell_to_px(fit, W, H, ax, ay)
    return common.cam_anchor((ax, ay), (lerp(hx, W / 2, e), lerp(hy, S12_STAGE_CY, e)), ca)


def S12(ctx, t_local, frame):
    t = ctx.t
    f = ctx.facts
    player = ctx.runs.player("longest")
    step = _s12_step(ctx, frame)
    player.seek(step)
    steps_drawn = step - _s12_step(ctx, frame - 1)
    img = common.render_run(player, _s12_camera(ctx, frame), steps_drawn=steps_drawn)
    at_onset = step >= f.longest_onset
    common.draw_counter(img, min(step, f.longest_onset), x=100, y=1180, size=60, running=not at_onset)  # freezes cream
    op, _ = card_anim(t, 50.0, HOLD)
    common.draw_bar_chart(img, f.histogram_log_bins, box=S12_CHART_BOX,
                          markers=[(f.longest_onset, "longest", AMBER), (f.onset, "empty grid", SECONDARY)],
                          title=f"onset step, all {fmt_int(f.n4)} 4x4 starts", opacity=op)
    if f.longest_origin == "adversarial":       # the first-person line only when the search produced the winner
        card_a = [Line("I evolved starts to stall it.", "regular", 56)]
    else:
        card_a = [Line("The stubbornest start we found:", "regular", 52)]
    card_a.append(Line(f.longest_source, "mono", 44, SECONDARY))
    op, dy = card_anim(t, 50.0, 53.5)
    common.draw_card(img, card_a, top=250, opacity=op, dy=dy)
    card_b = [Line(f"Longest delay: {f.longest_onset_fmt} steps.", "regular", 56)]
    if frame >= frame_of(S12_T_ONSET):
        card_b.append(Line("Still a road.", "bold", 84, gap_before=8))
    op, dy = card_anim(t, 53.5, HOLD)
    common.draw_card(img, card_b, top=250, opacity=op, dy=dy)
    # audio: the run's own crackle from 50.6, rub cluster with rising cutoff, clock ticks, then resolution
    events = []
    for k in range(int((S12_T_ONSET - 50.0) / 0.5) + 1):
        if ctx.at(frame, 50.0 + 0.5 * k) and 50.0 + 0.5 * k < S12_T_ONSET:
            events.append({"type": "tick"})
    if ctx.at(frame, S12_T_ONSET):
        events.append({"type": "thump"})
    osc = [{"run": "longest", "step": step, "gain_db": -16.0}] if frame > frame_of(S12_T_RUN) else []
    if at_onset:
        pad = {"chord": "highway", "cutoff": 1200.0, "detune_cents": 0.0, "gain_db": PAD_FULL_DB}
    else:
        u = clamp((t - S12_T_RUN) / (S12_T_ONSET - S12_T_RUN))
        pad = {"chord": ["A2", "Bb2", "Bb3", "E4", "F4"], "cutoff": lerp(400.0, 2500.0, u),
               "detune_cents": 8.0 * u, "gain_db": PAD_FULL_DB}
    return img, audio_state(osc=osc, pad=pad), events


# --------------------------------------------------------------------------
# S13 VERDICT (57.0-62.0)
# --------------------------------------------------------------------------

S13_LINE_T = (57.0, 57.4, 57.8)
S13_LINE_Y = (520, 620, 720)
S13_BODY_T = 59.5
S13_BODY_Y = (1000, 1090)
S13_X = 100


def _s13_lines(f) -> list[Line]:
    """The three verdict lines (honesty rule: cap hits -> 'N still unresolved.' in red)."""
    l1 = Line(f"{f.total_tested_fmt} runs tested.", "mono", 64)   # runs: nested boxes / repeat genomes are counted
    l2 = Line(f"{fmt_int(f.total_highway)} highways.", "mono", 64)
    if f.cap_hits > 0:
        l3 = Line(f"{fmt_int(f.cap_hits)} still unresolved.", "mono", 64, RED)
    else:
        n = fmt_int(f.exceptions)
        l3 = Line(f"{n} exceptions.", "mono", 64, spans={n: AMBER})
    lines = [l1, l2, l3]
    size = min(common.fit_font("mono", 64, ln.text)[1] for ln in lines)   # one size for all three
    for ln in lines:
        ln.size = size
    return lines


def _draw_left_line(img, line: Line, top: float, t: float, t_in: float, snap: bool):
    """A single left-aligned line on the plain background with its glyph box top at `top`."""
    op, dy = card_anim(t, t_in, HOLD, snap_in=snap)
    common.draw_card(img, [line], top=top - common.BAND_PAD, x_left=S13_X, align="left",
                     opacity=op, dy=dy, band=False)


def S13(ctx, t_local, frame):
    t = ctx.t
    img = common.blend_frames(common.new_frame(PLAIN), ctx.road_backdrop(989), 0.15)
    for line, y, t_in in zip(_s13_lines(ctx.facts), S13_LINE_Y, S13_LINE_T):
        _draw_left_line(img, line, y, t, t_in, snap=True)
    body = (Line("That's evidence.", "bold", 72), Line("Not a proof.", "bold", 72, AMBER))
    for line, y in zip(body, S13_BODY_Y):
        _draw_left_line(img, line, y, t, S13_BODY_T, snap=False)
    events = [{"type": "thud"} for t_in in S13_LINE_T if ctx.at(frame, t_in)]
    pad = None if t >= S13_BODY_T else {"chord": "highway", "cutoff": 1200.0, "gain_db": PAD_THIN_DB}
    osc = [{"run": "empty", "step": ctx.step_at(frame), "gain_db": -22.0}]
    return img, audio_state(osc=osc, pad=pad), events


# --------------------------------------------------------------------------
# S14 SCORECARD (62.0-68.0)
# --------------------------------------------------------------------------

S14_LINE_T = (62.0, 64.0, 65.5)            # line 3 at 65.5 (not 66.0) so UNPROVEN holds >= 2 s at full opacity
S14_LINE_Y = (420, 760, 1100)
S14_X = 100
S14_ANT_DX, S14_ANT_DY = 180, 540          # the ant's screen offset from the centre toward the highway corner: (360, 1500) for -x,-y
S14_ROWS = (
    ("PROVEN", "It never gets trapped.", "Bunimovich & Troubetzkoy 1992"),
    ("PROVEN", "It can run any logic circuit.", "Gajardo, Moreira & Goles 2002"),
    ("UNPROVEN", "It always builds the road.", "every finite start, tested: yes"),
)


def _draw_score_row(img, row, y, t, t_in):
    """Pill above the sentence, citation beneath, on the standard band (the 25 % highway runs
    under the text otherwise); UNPROVEN gets a slow pulsing amber underline."""
    kind, sentence, citation = row
    op, dy = card_anim(t, t_in, HOLD)
    if op <= 0:
        return
    lines = [Line(sentence, "regular", 56), Line(citation, "mono", 40, SECONDARY, gap_before=4)]
    _, box = common.draw_pill_card(img, kind, lines, top=y, opacity=op, dy=dy, x=S14_X)
    if kind == "UNPROVEN" and box is not None:
        fnt, _ = common.fit_font("regular", 56, sentence)
        asc, desc = fnt.getmetrics()
        ly = box[1] + common.BAND_PAD + (asc + desc) * LINE_SPACING - 2
        pulse = 0.55 + 0.45 * math.sin(2 * math.pi * 0.5 * (t - t_in) - math.pi / 2)
        _underline(img, S14_X, S14_X + fnt.getlength(sentence), ly, op * pulse)


def _s14_camera(ctx, player) -> Camera:
    """Follow-cam, 135 cells across, with the ant anchored below the three rows (row 3's band
    ends at ~1382) and toward the highway corner (derived from highway_sign), so the ant and the
    amber road tip are never under a card and the road runs diagonally across the frame."""
    sx, sy = ctx.facts.highway_sign
    ax, ay = player.ant_xy
    return common.cam_anchor((ax + 0.5, ay + 0.5), (W / 2 + sx * S14_ANT_DX, H / 2 - sy * S14_ANT_DY), 135)


def S14(ctx, t_local, frame):
    t = ctx.t
    player = ctx.runs.player("empty")
    player.seek(ctx.step_at(frame))
    grid = common.render_run(player, _s14_camera(ctx, player), steps_drawn=ctx.steps_drawn(frame))
    img = common.blend_frames(common.new_frame(PLAIN), grid, 0.25)
    for row, y, t_in in zip(S14_ROWS, S14_LINE_Y, S14_LINE_T):
        _draw_score_row(img, row, y, t, t_in)
    events = [{"type": "bell"} for row, t_in in zip(S14_ROWS, S14_LINE_T) if row[0] == "PROVEN" and ctx.at(frame, t_in)]
    open_line = t >= S14_LINE_T[2]
    osc = [] if open_line else [{"run": "empty", "step": ctx.step_at(frame), "gain_db": -22.0}]
    pad = None if open_line else {"chord": "highway", "cutoff": 1200.0, "gain_db": PAD_THIN_DB}
    return img, audio_state(osc=osc, pad=pad), events
