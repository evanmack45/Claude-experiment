"""Road chapter scenes: S01-S08 and S15 (STORYBOARD 3.2) plus `road_backdrop`.

  S01 hook            static 130-cell camera (blob at screen (590, 1090)), the road erupts on frame 15
  S02 / S03 rules     9-cell camera, three-phase step animation (rotate, wipe, slide)
  S04 whole program   zoom-out 9 -> 27 cells while the rate ramps 2 -> 60 steps/s
  S05 chaos           ease-out zoom 27 -> 90 cells, counter lands on the onset at frame 480
  S06 freeze          frozen at the onset: 2 % push-in, pulsing amber ring, hard silence
  S07 the road        104 steps per frame, follow-cam then pull-back, frozen barcode
  S08 to infinity     auto pull-back to ~1 px/cell, PROVEN pill
  S15 CTA             mirrors S01, decelerating plucks, fade to plain (complete on the last frame)

Every number on screen comes from ctx.facts or the step schedule (SCENES_CONTRACT 3.1);
the camera centres of S01/S07/S08/S15 are derived from ctx.facts.highway_sign.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

import common
import core
from common import (AMBER, BLUE, CREAM, FPS, H, PLAIN, SECONDARY, VISITED, W, Line, audio_state,
                    card_anim, clamp, frame_of, lerp, smoothstep)
from core import Camera, ease_out_cubic

# --------------------------------------------------------------------------
# Timing constants (STORYBOARD 3.1 / 3.2 / 4.2)
# --------------------------------------------------------------------------

DEMO_FIRE = (2.3, 2.8, 3.3, 3.8, 4.9, 5.4, 5.9, 6.4, 6.9)   # absolute s of demo steps 1..9
ROT_S, FILL_S, SLIDE_S = 0.12, 0.15, 0.18                    # three phases of a demo step
DEMO_END = DEMO_FIRE[-1] + ROT_S + FILL_S + SLIDE_S           # 7.35 s: step 9's slide ends inside S04
BLOB_LAG_F0 = frame_of(7.0)          # the blob-centre lag runs from the start of S04 through S05
HANDOFF_S = 0.6                      # eased camera hand-offs (S06->S07, S07 follow -> pull-back)
PLUCK_MAX_RATE = 20.0                # steps/s: plucks below, turn-stream oscillator above
XFADE_S = 0.5                        # pluck <-> oscillator crossfade
S04_PLUCK_END = 7.0 + 3.0 * math.log(PLUCK_MAX_RATE / 2.0) / math.log(30.0)   # r(t) = 2*30^((t-7)/3) hits 20
T_S15 = common.T_S15                 # 73.0 s (the WALLS insert shifted S13-S15 by +5.0 s)
S15_DECEL = ((4.0, 4.4, 3000.0, 8.0), (4.4, 5.5, 8.0, 2.0))  # (t0, t1, r0, r1) local s, exponential legs
S15_DRIFT = (2.0, 3.0)               # local s: the camera leaves the hook framing at +2.0 and settles on the ant at +3.0
S15_LOCK = S15_DECEL[0][0]           # local s: the camera stops following at +4.0, the ant then hops in view
S15_TIP_CELLS = 90                   # cells across once settled (12 px/cell: single steps are visible)
S15_TIP_SCREEN = (W / 2, 1170)       # the ant's screen position once settled: the text-free band between the sub-lines (end ~903) and the credit (1437)
S15_DRIFT_CTRL = (100, 1290)         # Bezier control: the ant comes back along the lower-left, above the credit band
S15_QUESTION_TOP = 280               # question band top (ends ~626): >= 20 px above the sub-lines band, and >= 240 (safe zone)
S15_SUB_TOP = 650                    # sub-lines band top: 24 px under the question band (280 .. ~626), STORYBOARD "640-830"; its bottom (~903) clears the hook blob
S15_CREDIT_LINES = (Line("made by Claude (an AI)", "mono", 40, SECONDARY),
                    Line("github: evanmack45/langtons-ant-highway", "mono", 36, SECONDARY))
S15_CREDIT_BOTTOM = common.SAFE_Y1   # the credit band is bottom-aligned to the safe zone (1437 .. 1600, measured), reviewer V1 / SCI-02
S15_FADE_LOCAL = 5.5                 # local s: the fade to plain starts here and completes on the last frame
HOOK_CELLS = 130                     # S01 / S15: cells across (8.3 px/cell), director's cut
HOOK_BLOB_DXY = (50, 130)            # the blob centre sits this far from the frame centre, away from the highway corner: (590, 1090) for -x,-y
HOLD = 1e9                           # card end time "hold to the hard cut"
PLUCK_FULL_RATE = 4.0                # steps/s: plucks at full gain up to here ...
PLUCK_DB_PER_DOUBLING = 3.5          # ... then -3.5 dB per doubling of the rate (S04: 20 stacked 350 ms plucks were the loudest passage, reviewer T-01)


def _s15_credit_top() -> float:
    """Credit band top: its measured height above S15_CREDIT_BOTTOM (1437.05 for Mono 40 + Mono 38)."""
    h = 2 * common.BAND_PAD + sum(sum(common.fit_font(ln.role, ln.size, ln.text)[0].getmetrics()) * common.LINE_SPACING
                                  for ln in S15_CREDIT_LINES)
    return S15_CREDIT_BOTTOM - h


def _pluck_gain_db(rate: float) -> float:
    """Pluck gain versus the instantaneous step rate: 0 dB up to PLUCK_FULL_RATE, then
    -PLUCK_DB_PER_DOUBLING per doubling, so a cascade of overlapping plucks does not bulge."""
    return -PLUCK_DB_PER_DOUBLING * max(0.0, math.log2(max(rate, 1e-9) / PLUCK_FULL_RATE))


def _rate_crossing(legs, rate: float) -> float:
    """Local time at which the exponential legs first fall to `rate` steps/s."""
    for t0, t1, r0, r1 in legs:
        if r1 <= rate <= r0:
            return t0 + (t1 - t0) * math.log(rate / r0) / math.log(r1 / r0)
    raise ValueError(f"rate {rate} outside the deceleration legs")


S15_PLUCK_START = _rate_crossing(S15_DECEL, PLUCK_MAX_RATE)   # local ~4.34 s (77.34 s): tone -> per-step plucks

ARROW_L = (190, 215, 255)            # "blue-white" left-turn arrow
SCREEN_ANGLE = {0: -90.0, 1: 0.0, 2: 90.0, 3: 180.0}   # heading (N,E,S,W) -> screen angle, y down
WHITE = (255, 255, 255)

_S15_SCHEDULES: dict[int, np.ndarray] = {}


# --------------------------------------------------------------------------
# Small drawing helpers (private to the road chapter)
# --------------------------------------------------------------------------

def _label(img: Image.Image, text: str, x: float, y: float, *, size: int = 40, color=SECONDARY, opacity: float = 1.0):
    """Mono label on a compact band; (x, y) = left edge and vertical centre (like draw_counter)."""
    if opacity <= 0:
        return
    fnt, _ = common.fit_font("mono", size, text)
    asc, desc = fnt.getmetrics()
    tw, th = fnt.getlength(text), asc + desc
    pad = 14
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * clamp(opacity))
    bx0, bx1 = common.clamp_band_x(x - pad, x + tw + pad)
    d.rounded_rectangle([bx0, y - th / 2 - pad, bx1, y + th / 2 + pad], radius=16,
                        fill=(*PLAIN, int(common.BAND_ALPHA * a)))
    d.text((x, y - th / 2), text, font=fnt, fill=(*color, a))
    img.paste(layer, (0, 0), layer)


def _draw_ant_chevron(img: Image.Image, px: float, py: float, angle: float, cell_px: float):
    """The >= 60 px ant (glow + heading chevron) at an arbitrary screen angle (degrees, y down)."""
    r = cell_px * 0.5
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i, alpha in ((1.3, 50), (1.1, 80)):
        d.ellipse([px - r * i, py - r * i, px + r * i, py + r * i], fill=(*BLUE, alpha))
    pts = []
    for a_off in (0, 140, 220):
        a = math.radians(angle + a_off)
        rr = r if a_off == 0 else r * 0.9
        pts.append((px + rr * math.cos(a), py + rr * math.sin(a)))
    d.polygon(pts, fill=(*BLUE, 255))
    img.paste(layer, (0, 0), layer)


def _draw_turn_arrow(d: ImageDraw.ImageDraw, cx: float, cy: float, radius: float, a0: float, sweep: float,
                     clockwise: bool, opacity: float):
    """Curved arrow around (cx, cy) from screen angle a0 sweeping `sweep` degrees (amber
    clockwise for a right turn, blue-white counter-clockwise for a left turn)."""
    if sweep < 2 or opacity <= 0:
        return
    col = AMBER if clockwise else ARROW_L
    a = int(255 * clamp(opacity))
    box = [cx - radius, cy - radius, cx + radius, cy + radius]
    if clockwise:
        d.arc(box, start=a0, end=a0 + sweep, fill=(*col, a), width=6)
        tip_a, tdir = a0 + sweep, 1.0
    else:
        d.arc(box, start=a0 - sweep, end=a0, fill=(*col, a), width=6)
        tip_a, tdir = a0 - sweep, -1.0
    ar = math.radians(tip_a)
    px, py = cx + radius * math.cos(ar), cy + radius * math.sin(ar)
    tx, ty = -math.sin(ar) * tdir, math.cos(ar) * tdir       # travel direction along the arc
    nx, ny = math.cos(ar), math.sin(ar)                      # outward normal
    s = radius * 0.28
    d.polygon([(px + tx * s, py + ty * s),
               (px - tx * s * 0.2 + nx * s * 0.6, py - ty * s * 0.2 + ny * s * 0.6),
               (px - tx * s * 0.2 - nx * s * 0.6, py - ty * s * 0.2 - ny * s * 0.6)], fill=(*col, a))


def _draw_cell_outline(img: Image.Image, cam: Camera, x: int, y: int, opacity: float, width: int = 5):
    """Pulsing outline just outside one cell (S03 hold); cream so it reads against the amber cell."""
    x0, y0 = core.cell_to_px(cam, W, H, x, y + 1)
    x1, y1 = core.cell_to_px(cam, W, H, x + 1, y)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle([x0 - 6, y0 - 6, x1 + 6, y1 + 6], outline=(*CREAM, int(255 * clamp(opacity))), width=width)
    img.paste(layer, (0, 0), layer)


def _draw_ring(img: Image.Image, cam: Camera, ant_xy, t_local: float):
    """3-cell amber ring pulsing (1 Hz) around the frozen ant (S06)."""
    ax, ay = ant_xy
    px, py = core.cell_to_px(cam, W, H, ax + 0.5, ay + 0.5)
    cell_px = W / cam.cells_across
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * 1.0 * t_local - math.pi / 2)   # 0 at t=0, 1 Hz
    r = cell_px * (3.0 + 0.5 * pulse)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([px - r, py - r, px + r, py + r], outline=(*AMBER, int(255 * (0.4 + 0.6 * (1 - pulse)))), width=4)
    img.paste(layer, (0, 0), layer)


# --------------------------------------------------------------------------
# Cameras (STORYBOARD 2.5 / 3.2)
# --------------------------------------------------------------------------

def _hook_camera(ctx) -> Camera:
    """S01 / S15: static, HOOK_CELLS across; the blob centre (centroid of the cells modified up to the
    onset) sits at screen (W/2 - sx*50, H/2 - sy*130) = (590, 1090) for the -x,-y highway, so the road
    erupts from the blob and reaches the lower-left frame edge at ~1.4 s; the blob's top clears the
    S15 sub-lines band (ends ~903) by ~23 px and the road crosses x = 80 above the credit band (top
    1437) by ~27 px (both computed from the run's cells at 74.8 s)."""
    sx, sy = ctx.facts.highway_sign
    return common.cam_anchor(_blob_at_onset(ctx), (W / 2 - sx * HOOK_BLOB_DXY[0], H / 2 - sy * HOOK_BLOB_DXY[1]), HOOK_CELLS)


def _s15_camera(ctx, frame: int, t_local: float) -> Camera:
    """S15: the S01 camera until +2.0 s (the first 60 frames mirror S01); then a 1 s smoothstep
    drift that carries the ant from where the hook framing shows it at +2.0 along a quadratic
    Bezier (along the lower-left, above the credit band) to the centre of the text-free band
    while zooming 130 -> 90 cells; the camera follows the ant until +4.0 and then locks, so the
    decelerating steps are seen as the ant hopping cell by cell (the ant leaves the static hook
    frame at ~+1.5 s, before the audible slow-down)."""
    hook = _hook_camera(ctx)
    d0, d1 = S15_DRIFT
    if t_local <= d0:
        return hook
    sched = _s15_schedule(ctx)
    pos = ctx.runs.run("empty").pos

    def ant_at(f):
        return tuple(float(v) + 0.5 for v in pos[int(sched[f - ctx.shot.f0])])

    ant = ant_at(min(frame, frame_of(T_S15 + S15_LOCK)))
    e = smoothstep((t_local - d0) / (d1 - d0))
    ca = math.exp(lerp(math.log(hook.cells_across), math.log(S15_TIP_CELLS), e))
    p0 = core.cell_to_px(hook, W, H, *ant_at(frame_of(T_S15 + d0)))
    w0, w1, w2 = (1 - e) ** 2, 2 * e * (1 - e), e ** 2
    target = tuple(w0 * p0[i] + w1 * S15_DRIFT_CTRL[i] + w2 * S15_TIP_SCREEN[i] for i in range(2))
    return common.cam_anchor(ant, target, ca)


def _demo_camera() -> Camera:
    """S02 / S03: static, centre (0.5, -0.5), 9 cells across (120 px/cell)."""
    return common.cam_static(0.5, -0.5, 9)


def _blob_center(ctx, frame: int) -> np.ndarray:
    """Centroid of the modified cells at the displayed step, lagged 0.3 s from the start of S04."""
    stats = ctx.runs.stats("empty")
    return ctx.lag.value("road_blob", frame, BLOB_LAG_F0, lambda f: stats.centroid_at(max(1, ctx.step_at(f))))


def _s04_camera(ctx, frame: int, t_local: float) -> Camera:
    cx, cy = _blob_center(ctx, frame)
    return common.cam_tween(_demo_camera(), Camera(cx, cy, 27), t_local / 3.0)


def _s05_camera(ctx, frame: int, t_local: float) -> Camera:
    """Ease-out zoom 27 -> 90 cells on the lagged blob centre; the blob is kept inside the
    middle 60 % of the frame by widening the view when its bbox outgrows that."""
    cx, cy = _blob_center(ctx, frame)
    x0, y0, x1, y1 = ctx.runs.stats("empty").bbox_at(ctx.step_at(frame))
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    ca = max(lerp(27.0, 90.0, ease_out_cubic(t_local / 6.0)), (bw + 4) / 0.6, (bh + 4) * (W / H) / 0.6)
    return Camera(cx, cy, ca)


def _s06_camera(ctx, t_local: float) -> Camera:
    """2 % push-in over 4 s toward the ant, continuous with the last S05 camera."""
    f_end = frame_of(16.0) - 1
    base = _s05_camera(ctx, f_end, f_end / FPS - 10.0)
    ax, ay = ctx.runs.run("empty").pos[ctx.facts.onset]
    s = 1.0 - 0.02 * clamp(t_local / 4.0)
    return Camera(ax + 0.5 + (base.cx - ax - 0.5) * s, ay + 0.5 + (base.cy - ay - 0.5) * s, base.cells_across * s)


def _blob_at_onset(ctx):
    return ctx.runs.stats("empty").centroid_at(ctx.facts.onset)


def _s07_camera(ctx, player, t_local: float) -> Camera:
    """Follow-cam (108 cells) after a 0.6 s ease from S06; 0.6 s hand-off into the pull-back rule at 24.0."""
    follow = common.cam_follow(player, 108)
    if t_local < HANDOFF_S:
        return common.cam_tween(_s06_camera(ctx, 4.0), follow, t_local / HANDOFF_S)
    if t_local < 4.0:
        return follow
    pull = common.cam_pullback(player.ant_xy, _blob_at_onset(ctx))
    if t_local < 4.0 + HANDOFF_S:
        return common.cam_tween(follow, pull, (t_local - 4.0) / HANDOFF_S)
    return pull


def _s08_camera(ctx, player, t_local: float) -> Camera:
    """Auto pull-back rule; the centre drifts (smoothstep over the shot) so the blob ends up
    near screen (760, 700) - mirrored by highway_sign - and the road runs to the corner."""
    bx, by = _blob_at_onset(ctx)
    pull = common.cam_pullback(player.ant_xy, (bx, by))
    sx, sy = ctx.facts.highway_sign
    target_x, target_y = W / 2 - sx * 220, H / 2 + sy * 260
    cell_px = W / pull.cells_across
    cx = bx - (target_x - W / 2) / cell_px
    cy = by + (target_y - H / 2) / cell_px
    u = smoothstep(t_local / 6.0)
    return Camera(lerp(pull.cx, cx, u), lerp(pull.cy, cy, u), pull.cells_across)


# --------------------------------------------------------------------------
# Rules demo (S02 / S03 and the first 0.35 s of S04)
# --------------------------------------------------------------------------

def _demo_phase(t_abs: float) -> tuple[int, float, float, float]:
    """(k, rot, fill, slide): the demo step in flight (0 = none yet) and its phase progresses 0..1."""
    k = sum(1 for tf in DEMO_FIRE if t_abs >= tf)
    if k == 0:
        return 0, 1.0, 1.0, 1.0
    dt = t_abs - DEMO_FIRE[k - 1]
    return k, clamp(dt / ROT_S), clamp((dt - ROT_S) / FILL_S), clamp((dt - ROT_S - FILL_S) / SLIDE_S)


def _demo_picture(ctx, cam: Camera, t_abs: float) -> Image.Image:
    """Grid + three-phase animated ant of the rules demo at absolute time t_abs.

    rotate (120 ms, curved arrow) -> radial wipe of the cell (150 ms) -> eased slide (180 ms).
    The grid shows step k-1 until the wipe completes, then step k (the fresh cell is amber
    or, when erased, the visited tint - the same colours render_run uses)."""
    run, player = ctx.runs.run("empty"), ctx.runs.player("empty")
    k, rot, fill, slide = _demo_phase(t_abs)
    player.seek(k if fill >= 1.0 else k - 1)
    img = common.render_run(player, cam, ant=False)
    cell_px = W / cam.cells_across
    k0 = max(k - 1, 0)
    x0, y0 = (float(v) for v in run.pos[k0])
    x1, y1 = (float(v) for v in run.pos[k])
    a0 = SCREEN_ANGLE[int(run.dir[k0])]
    is_r = k > 0 and int(run.turns[k - 1]) == 1
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if 0.0 < fill < 1.0:
        cx0, cy0 = core.cell_to_px(cam, W, H, x0, y0 + 1)
        cx1, cy1 = core.cell_to_px(cam, W, H, x0 + 1, y0)
        col = AMBER if is_r else VISITED
        d.pieslice([cx0 + 1, cy0 + 1, cx1 - 1, cy1 - 1], start=-90, end=-90 + 360 * fill, fill=(*col, 255))
    u = smoothstep(slide)
    px, py = core.cell_to_px(cam, W, H, lerp(x0, x1, u) + 0.5, lerp(y0, y1, u) + 0.5)
    angle = a0
    if k > 0:
        angle = a0 + (90.0 if is_r else -90.0) * smoothstep(rot)
        if fill < 1.0:
            _draw_turn_arrow(d, px, py, cell_px * 0.62, a0, 90.0 * smoothstep(rot), is_r, 1.0 if rot < 1.0 else 1.0 - fill)
    img.paste(layer, (0, 0), layer)
    _draw_ant_chevron(img, px, py, angle, cell_px)
    return img


def _demo_events(ctx, frame: int, first_step: int, last_step: int) -> list[dict]:
    """Pluck at each demo step's turn (its listed time) and a 3 ms click at the flip 120 ms later."""
    events = []
    for k in range(first_step, last_step + 1):
        t_fire = DEMO_FIRE[k - 1]
        if ctx.at(frame, t_fire):
            events.append({"type": "pluck", "run": "empty", "step": k})
        if ctx.at(frame, t_fire + ROT_S):
            events.append({"type": "click"})
    return events


def _rules_shot(ctx, frame: int, *, t0: float, t1: float, first_step: int, last_step: int,
                lines: list[Line], label: str):
    """Shared body of S02 / S03: demo picture, rule card (band top 260), label at (100, 1520)."""
    cam = _demo_camera()
    img = _demo_picture(ctx, cam, ctx.t)
    if ctx.t < DEMO_FIRE[first_step - 1] and first_step > 1:          # S03 hold: pulsing outline on the marked origin
        pulse = 0.55 + 0.45 * math.sin(2 * math.pi * 2.5 * (ctx.t - t0))
        _draw_cell_outline(img, cam, 0, 0, pulse)
    op, dy = card_anim(ctx.t, t0, t1)
    common.draw_card(img, lines, top=260, opacity=op, dy=dy)
    _label(img, label, 100, 1520, opacity=op)
    return img, audio_state(), _demo_events(ctx, frame, first_step, last_step)


# --------------------------------------------------------------------------
# S15 private step schedule (deceleration; common.build_step_schedule holds 3,000 steps/s)
# --------------------------------------------------------------------------

def _s15_rate(tl: float) -> float:
    """Displayed steps/s in S15 at local time tl: 3,000 until +4.0, then exponential legs 3,000 -> 8 -> 2."""
    if tl < S15_DECEL[0][0]:
        return S15_DECEL[0][2]
    for t0, t1, r0, r1 in S15_DECEL:
        if tl < t1:
            return r0 * (r1 / r0) ** ((tl - t0) / (t1 - t0))
    return 0.0


def _s15_schedule(ctx) -> np.ndarray:
    """Displayed step per S15 local frame: the common schedule (mirrors S01) until +4.0 s, then the
    3,000 -> 8 -> 2 steps/s deceleration whose last step fires exactly at +5.5 s and is a left turn
    (the closing A3 pluck); the picture holds from +5.5 to the cut."""
    key = id(ctx)
    if key in _S15_SCHEDULES:
        return _S15_SCHEDULES[key]
    f0, n = frame_of(T_S15), frame_of(common.DURATION_S) - frame_of(T_S15)
    steps = np.array([ctx.step_at(f0 + i) for i in range(n)], dtype=np.int64)
    fa, fb = frame_of(T_S15 + S15_DECEL[0][0]) - f0 - 1, frame_of(T_S15 + S15_DECEL[1][1]) - f0   # cumulative count starts at frame fa
    sub = 100
    cum = np.zeros(fb - fa + 1)
    for j in range(fb - fa):
        ts = (fa + j) / FPS + (np.arange(sub) + 0.5) / (FPS * sub)
        cum[j + 1] = cum[j] + sum(_s15_rate(t) for t in ts) / (FPS * sub)
    base, total = int(steps[fa]), float(cum[-1])
    n_int = int(round(total))
    if int(ctx.runs.turns("empty")[base + n_int - 1]) == 1:      # end on a left turn
        n_int += 1
    scaled = cum * (n_int / total)
    for j in range(1, fb - fa + 1):
        steps[fa + j] = base + int(math.floor(scaled[j] + 1e-9))
    steps[fb:] = base + n_int
    _S15_SCHEDULES[key] = steps
    return steps


# --------------------------------------------------------------------------
# Scenes
# --------------------------------------------------------------------------

def road_backdrop(ctx, frame: int) -> Image.Image:
    """Grid-only picture of the empty-grid run as S08 draws it at `frame` (no text).

    Used behind S09 (20 %) and S13 (15 %) via ctx.road_backdrop(989).
    """
    player = ctx.runs.player("empty")
    player.seek(ctx.step_at(frame))
    cam = _s08_camera(ctx, player, frame / FPS - 27.0)
    return common.render_run(player, cam, steps_drawn=ctx.steps_drawn(frame))


def S01(ctx, t_local, frame):
    """HOOK: the run resumes 1,500 steps before the onset; the road erupts at 0.5 s."""
    step = ctx.step_at(frame)
    player = ctx.runs.player("empty")
    player.seek(step)
    img = common.render_run(player, _hook_camera(ctx), steps_drawn=ctx.steps_drawn(frame))
    lines = []
    if t_local >= 0.2:
        lines.append(Line("2 rules.", "bold", 104))
    if t_local >= 0.9:
        lines.append(Line("Then THIS happens.", "bold", 76))
    if lines:
        common.draw_card(img, lines, top=300)
    common.draw_counter(img, step, running=True)
    events = [{"type": "thump"}] if ctx.at(frame, 0.5) else []
    return img, audio_state(osc={"run": "empty", "step": step, "gain_db": -18.0}), events


def S02(ctx, t_local, frame):
    """RULE 1: steps 1-4 on the empty grid, four right turns."""
    return _rules_shot(ctx, frame, t0=2.0, t1=4.5, first_step=1, last_step=4,
                       lines=[Line("Empty cell?", "regular", 60),
                              Line("Turn RIGHT, mark it, step.", "regular", 56, spans={"RIGHT": AMBER})],
                       label="rule 1 of 2")


def S03(ctx, t_local, frame):
    """RULE 2: 0.4 s hold on the marked origin, then steps 5-9 with their real turns."""
    return _rules_shot(ctx, frame, t0=4.5, t1=7.0, first_step=5, last_step=9,
                       lines=[Line("Marked cell?", "regular", 60),
                              Line("Turn LEFT, erase it, step.", "regular", 56, spans={"LEFT": BLUE})],
                       label="rule 2 of 2")


def S04(ctx, t_local, frame):
    """WHOLE PROGRAM: rate 2 -> 60 steps/s, zoom-out 9 -> 27 cells; plucks hand over to the oscillator."""
    step = ctx.step_at(frame)
    cam = _s04_camera(ctx, frame, t_local)
    if ctx.t < DEMO_END:                               # step 9's slide finishes inside this shot
        img = _demo_picture(ctx, cam, ctx.t)
    else:
        player = ctx.runs.player("empty")
        player.seek(step)
        img = common.render_run(player, cam, steps_drawn=ctx.steps_drawn(frame))
    op, dy = card_anim(ctx.t, 7.0, 10.0)
    common.draw_card(img, [Line("That's it.", "bold", 96),
                           Line("The whole program.", "regular", 56),
                           Line("no randomness. no lookahead.", "mono", 44, SECONDARY, gap_before=16)],
                     top=300, opacity=op, dy=dy)
    op_counter, _ = card_anim(ctx.t, 7.0, HOLD)          # no fade-out: the counter continues into S05
    common.draw_counter(img, step, running=True, opacity=op_counter)
    # audio: plucks per step until 20 steps/s, then a 0.5 s crossfade into the turn stream
    events = _demo_events(ctx, frame, 9, 9)            # step 9's flip click lands at 7.02 s
    xf = clamp((ctx.t - S04_PLUCK_END) / XFADE_S)
    if xf < 1.0:
        g = _pluck_gain_db(2.0 * 30.0 ** ((ctx.t - 7.0) / 3.0))      # STORYBOARD 3.1: r(t) = 2 * 30^((t-7)/3)
        for k in range(ctx.step_at(frame - 1) + 1, step + 1):
            events.append({"type": "pluck", "run": "empty", "step": k, "gain_db": lerp(g, -30.0, xf)})
    osc = [{"run": "empty", "step": step, "gain_db": lerp(-40.0, -20.0, xf)}] if ctx.t >= S04_PLUCK_END else []
    return img, audio_state(osc=osc, drone={"add_e": True}), events


def S05(ctx, t_local, frame):
    """CHAOS: exponential ramp to the onset on frame 480, zoom 27 -> 90 cells, contrast cap."""
    step = ctx.step_at(frame)
    player = ctx.runs.player("empty")
    player.seek(step)
    img = common.render_run(player, _s05_camera(ctx, frame, t_local), steps_drawn=ctx.steps_drawn(frame))
    op, dy = card_anim(ctx.t, 10.0, 13.0)
    common.draw_card(img, [Line("No pattern. No repeats.", "regular", 60)], top=300, opacity=op, dy=dy)
    op, dy = card_anim(ctx.t, 13.0, 16.0)
    common.draw_card(img, [Line("Deterministic. Looks random.", "regular", 56)], top=300, opacity=op, dy=dy)
    common.draw_counter(img, step, running=True)
    u = t_local / 6.0
    state = audio_state(
        osc={"run": "empty", "step": step, "gain_db": lerp(-20.0, -16.0, u)},
        pad={"chord": "chaos", "cutoff": lerp(400.0, 2500.0, u), "detune_cents": lerp(0.0, 8.0, u)},
        drone={"add_e": True},
    )
    return img, state, []


def S06(ctx, t_local, frame):
    """FREEZE: frozen on the onset step; 6 % white flash on frame 480; hard silence then a long thump."""
    step = ctx.step_at(frame)
    player = ctx.runs.player("empty")
    player.seek(step)
    cam = _s06_camera(ctx, t_local)
    img = common.render_run(player, cam, steps_drawn=0)
    if ctx.at(frame, 16.0):
        img = Image.blend(img, Image.new("RGB", img.size, WHITE), 0.06)
    _draw_ring(img, cam, player.ant_xy, t_local)
    op, dy = card_anim(ctx.t, 16.0, 20.0, snap_in=True)
    common.draw_card(img, [Line(f"Step {ctx.facts.onset_fmt}.", "mono", 104),
                           Line("The mess is about to end.", "regular", 56)],
                     center_y=1160, opacity=op, dy=dy)      # over the lower blob; y = 880 would hide the ringed ant
    common.draw_counter(img, step, running=False)
    if frame < frame_of(16.4):                     # hard silence up to (not including) the thump frame
        state = audio_state(mute=True, drone={"on": False})
    elif frame < frame_of(18.0):
        state = audio_state(drone={"on": False})
    else:
        state = audio_state(drone={"gain_db": -30.0})
    events = [{"type": "thump_long", "tail": 2.0}] if ctx.at(frame, 16.4) else []
    return img, state, events


def S07(ctx, t_local, frame):
    """THE ROAD: 104 steps per frame; follow-cam, then pull-back; frozen barcode of the last 208
    highway turns (frame 600 resumes at the onset, so the window is full from frame 602)."""
    step = ctx.step_at(frame)
    player = ctx.runs.player("empty")
    player.seek(step)
    cam = _s07_camera(ctx, player, t_local)
    # 104 steps per frame > 100 for the whole shot, including frame 600 (the schedule holds the
    # onset there, so steps_drawn would be 0 on the onset frame alone): cap explicitly
    img = common.render_run(player, cam, steps_drawn=ctx.steps_drawn(frame), contrast_cap=True)
    period = ctx.facts.period
    op, dy = card_anim(ctx.t, 20.0, 23.0)
    common.draw_card(img, [Line("Then: a road.", "bold", 96)], top=300, opacity=op, dy=dy)
    op, dy = card_anim(ctx.t, 23.5, 27.0)
    common.draw_card(img, [Line(f"{period} steps. Repeats forever.", "regular", 56)], top=300, opacity=op, dy=dy)
    op_band, _ = card_anim(ctx.t, 20.0, 27.0)            # counter + strip: fade in while the first two windows fill, fade out into S08
    common.draw_counter(img, step, y=1380, size=48, running=True, suffix=f" · period {period}", opacity=op_band)
    common.draw_turn_strip(img, ctx.runs.turns("empty"), step, bracket=period, label=f"{period} turns",
                           opacity=op_band, first_step=ctx.facts.onset)
    events = []
    on_onset = ctx.at(frame, 20.0)
    if on_onset:
        events.append({"type": "thump"})
    if frame % FPS == 0 and not on_onset:                # the once-per-second kick never stacks on the onset thump
        events.append({"type": "kick"})
    state = audio_state(osc={"run": "empty", "step": step, "gain_db": -14.0},
                        pad={"chord": "highway", "cutoff": 1200.0, "detune_cents": 0.0})
    return img, state, events


def S08(ctx, t_local, frame):
    """TO INFINITY: the pull-back continues to ~1 px/cell; 'It never turns back.' then the PROVEN card."""
    step = ctx.step_at(frame)
    player = ctx.runs.player("empty")
    player.seek(step)
    img = common.render_run(player, _s08_camera(ctx, player, t_local), steps_drawn=ctx.steps_drawn(frame))
    op, dy = card_anim(ctx.t, 27.0, 30.0)
    common.draw_card(img, [Line("It never turns back.", "bold", 72)], top=300, opacity=op, dy=dy)
    op, dy = card_anim(ctx.t, 30.0, 33.0, snap_out=True)
    common.draw_pill_card(img, "PROVEN", [Line("No finite start can trap the ant.", "regular", 48),
                                          Line("Bunimovich & Troubetzkoy, 1992", "mono", 40, SECONDARY)],
                          top=300, opacity=op, dy=dy)
    events = []
    if ctx.at(frame, 27.0):
        events.append({"type": "riser", "dur": 3.0})
    if ctx.at(frame, 30.0):
        events.append({"type": "bell", "freq": 880.0, "decay": 2.0})
    state = audio_state(osc={"run": "empty", "step": step, "gain_db": -14.0},
                        pad={"chord": "highway_shimmer", "cutoff": 1200.0, "detune_cents": 0.0})
    return img, state, events


def S15(ctx, t_local, frame):
    """CTA: the hook replays (same camera and run until +2.0, then a drift onto the ant); the tone
    hands over to slowing plucks; fade to plain."""
    sched = _s15_schedule(ctx)
    i = ctx.local_frame(frame)
    step = int(sched[i])
    player = ctx.runs.player("empty")
    player.seek(step)
    img = common.render_run(player, _s15_camera(ctx, frame, t_local),
                            steps_drawn=step - int(sched[i - 1]) if i > 0 else 0)
    t0, t_end = ctx.shot.t0, ctx.shot.t1
    op, dy = card_anim(ctx.t, t0 + 0.2, t_end, snap_out=True)
    common.draw_card(img, [Line("Can YOU find a start", "bold", 72), Line("that never", "bold", 72),
                           Line("builds a road?", "bold", 72)], top=S15_QUESTION_TOP, opacity=op, dy=dy)
    op, dy = card_anim(ctx.t, t0 + 0.6, t_end, snap_out=True)
    common.draw_card(img, [Line("Any finite start counts.", "regular", 48), Line("Proof or counterexample?", "regular", 48),
                           Line("Argue in the comments.", "regular", 48)], top=S15_SUB_TOP, opacity=op, dy=dy)
    op, dy = card_anim(ctx.t, t0 + 1.0, t_end, snap_out=True)
    common.draw_card(img, list(S15_CREDIT_LINES), top=_s15_credit_top(), opacity=op, dy=dy)
    f_fade, f_last = frame_of(t0 + S15_FADE_LOCAL), ctx.shot.f1 - 1
    if frame >= f_fade:                                  # fade to plain, reaching 100 % on the last frame
        img = Image.blend(img, Image.new("RGB", img.size, PLAIN), clamp((frame - f_fade) / (f_last - f_fade)))
    # audio: crackle -> tone on the onset frame, A major pad, tone -> plucks from ~+4.34 s, silence after +5.5
    events = [{"type": "thump"}] if ctx.at(frame, t0 + 0.5) else []
    xf = clamp((t_local - S15_PLUCK_START) / XFADE_S)
    if t_local >= S15_PLUCK_START and i > 0:
        for k in range(int(sched[i - 1]) + 1, step + 1):
            events.append({"type": "pluck", "run": "empty", "step": k})
    gain = -18.0 if t_local < 0.5 else lerp(-18.0, -14.0, clamp(t_local - 0.5))
    osc = [] if xf >= 1.0 else [{"run": "empty", "step": step, "gain_db": lerp(gain, -40.0, xf)}]
    pad = {"chord": "highway", "cutoff": 1200.0, "detune_cents": 0.0} if 0.5 <= t_local < 5.0 else None
    return img, audio_state(osc=osc, pad=pad, drone={"on": t_local < 5.0}), events
