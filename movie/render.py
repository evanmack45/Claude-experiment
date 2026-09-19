"""Frame loop + CLI for "Two Rules, One Road".

    PYTHONPATH=. python3 render.py --facts PATH --out build/video.mp4 \
        [--shots S01,S05] [--frames a:b] [--preview] [--dump-frames DIR] \
        [--timeline build/timeline.json] [--safe-zone]

For every frame f: t = f / 30, find the shot, call its scene function
(see SCENES_CONTRACT.md), write the frame, and record the returned audio
state + events into the timeline JSON that audio.py turns into a WAV.
The video written here is silent; audio.py muxes the final file.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
from dataclasses import dataclass

import numpy as np
from PIL import Image

import common
import core
from common import FPS, H, N_FRAMES, W, frame_of

# --------------------------------------------------------------------------
# Shot registry (STORYBOARD 3.2)
# --------------------------------------------------------------------------

SHOT_TABLE = [
    # id, t0, t1, module
    ("S01", 0.0, 2.0, "scenes_road"),
    ("S02", 2.0, 4.5, "scenes_road"),
    ("S03", 4.5, 7.0, "scenes_road"),
    ("S04", 7.0, 10.0, "scenes_road"),
    ("S05", 10.0, 16.0, "scenes_road"),
    ("S06", 16.0, 20.0, "scenes_road"),
    ("S07", 20.0, 27.0, "scenes_road"),
    ("S08", 27.0, 33.0, "scenes_road"),
    ("S09", 33.0, 38.0, "scenes_evidence"),
    ("S10", 38.0, 44.0, "scenes_evidence"),
    ("S11", 44.0, 50.0, "scenes_evidence"),
    ("S12", 50.0, 57.0, "scenes_evidence"),
    ("S13", 57.0, 62.0, "scenes_evidence"),
    ("S14", 62.0, 68.0, "scenes_evidence"),
    ("S15", 68.0, 74.0, "scenes_road"),
]


@dataclass
class Shot:
    id: str
    t0: float
    t1: float
    f0: int          # first frame (inclusive)
    f1: int          # last frame (exclusive)
    module: str
    fn: object = None

    @property
    def n_frames(self) -> int:
        return self.f1 - self.f0


def build_shots() -> list[Shot]:
    shots = []
    for sid, t0, t1, mod in SHOT_TABLE:
        shots.append(Shot(sid, t0, t1, frame_of(t0), frame_of(t1), mod))
    assert shots[-1].f1 == N_FRAMES, (shots[-1].f1, N_FRAMES)
    for a, b in zip(shots, shots[1:]):
        assert a.f1 == b.f0, (a, b)
    return shots


def resolve_scene(shot: Shot):
    if shot.fn is None:
        mod = importlib.import_module(shot.module)
        shot.fn = getattr(mod, shot.id)
    return shot.fn


# --------------------------------------------------------------------------
# Context handed to every scene function
# --------------------------------------------------------------------------

class Ctx:
    """Everything a scene may use (read-only from the scene's point of view).

    facts     : common.Facts (all numbers come from here)
    runs      : common.RunCache  -> runs.player("empty"), runs.stats("empty"), runs.turns(...)
    schedule  : np.ndarray, displayed empty-grid step per absolute frame (STORYBOARD 3.1)
    lag       : common.LagSmoother (0.3 s) - deterministic per-frame smoothing
    shot      : the current Shot (id, t0, t1, f0, f1)
    t         : absolute time of the current frame (s)
    preview   : True when rendering the half-resolution preview
    k4        : the k4 records {'cfg', 'status', 's'} shared with runs (dot wall)
    """

    def __init__(self, facts: common.Facts, preview: bool):
        self.facts = facts
        self.runs = common.RunCache(facts)
        self.schedule = common.build_step_schedule(facts.onset)
        self.lag = common.LagSmoother(tau=0.3)
        self.shot: Shot | None = None
        self.t = 0.0
        self.preview = preview
        self._backdrops: dict = {}

    # --- data ---------------------------------------------------------------
    @property
    def k4(self) -> dict:
        return self.runs.k4()

    def step_at(self, frame: int) -> int:
        """Displayed step of the empty-grid run at an absolute frame."""
        return int(self.schedule[int(common.clamp(frame, 0, N_FRAMES - 1))])

    def steps_drawn(self, frame: int) -> int:
        """Steps advanced between frame-1 and frame (drives the contrast cap)."""
        if frame <= 0:
            return 0
        return max(0, self.step_at(frame) - self.step_at(frame - 1))

    # --- timing -------------------------------------------------------------
    @staticmethod
    def frame_of(t_abs: float) -> int:
        return frame_of(t_abs)

    def at(self, frame: int, t_abs: float) -> bool:
        """True on exactly the frame where absolute time t_abs lands (for one-shot events)."""
        return frame == frame_of(t_abs)

    def local_frame(self, frame: int) -> int:
        return frame - self.shot.f0

    # --- shared backdrops ---------------------------------------------------
    def road_backdrop(self, frame: int = 989) -> Image.Image:
        """The S08 road frame (grid only, no text) used behind S09 and S13.
        Rendered once via scenes_road.road_backdrop and cached."""
        if frame not in self._backdrops:
            mod = importlib.import_module("scenes_road")
            self._backdrops[frame] = mod.road_backdrop(self, frame)
        return self._backdrops[frame]


# --------------------------------------------------------------------------
# Frame loop
# --------------------------------------------------------------------------

def parse_frames(spec: str | None, shots: list[Shot], shot_ids: list[str] | None) -> list[int]:
    frames: list[int] = []
    if shot_ids:
        wanted = {s.strip().upper() for s in shot_ids}
        unknown = wanted - {s.id for s in shots}
        if unknown:
            sys.exit(f"unknown shot ids: {sorted(unknown)}")
        for s in shots:
            if s.id in wanted:
                frames.extend(range(s.f0, s.f1))
    else:
        frames = list(range(N_FRAMES))
    if spec:
        a, b = spec.split(":")
        a = int(a) if a else 0
        b = int(b) if b else N_FRAMES
        frames = [f for f in frames if a <= f < b]
    return frames


def normalise_events(events, frame: int) -> list[dict]:
    out = []
    for ev in events or ():
        if not isinstance(ev, dict) or "type" not in ev:
            raise ValueError(f"bad audio event at frame {frame}: {ev!r}")
        e = dict(ev)
        e.setdefault("frame", frame)
        e["frame"] = int(e["frame"])
        out.append(e)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--facts", required=True, help="movie_facts.json (verified or provisional)")
    ap.add_argument("--out", required=True, help="silent H.264 output (mp4)")
    ap.add_argument("--shots", help="comma-separated shot ids, e.g. S01,S05")
    ap.add_argument("--frames", help="absolute frame range a:b (b exclusive)")
    ap.add_argument("--preview", action="store_true", help="write at 540x960 with a fast x264 preset")
    ap.add_argument("--dump-frames", metavar="DIR", help="also write every rendered frame as PNG")
    ap.add_argument("--timeline", default=os.path.join(common.BUILD_DIR, "timeline.json"))
    ap.add_argument("--safe-zone", action="store_true", help="overlay the text safe zone (debug)")
    ap.add_argument("--crf", type=int, default=21)
    args = ap.parse_args(argv)

    facts = common.load_facts(args.facts)
    print(f"[facts] {args.facts} provisional={facts.provisional} onset={facts.onset} longest={facts.longest_onset} "
          f"({facts.longest_origin}) total_tested={facts.total_tested} k5_bar={facts.show_k5}")
    shots = build_shots()
    frames = parse_frames(args.frames, shots, args.shots.split(",") if args.shots else None)
    if not frames:
        sys.exit("nothing to render")
    ctx = Ctx(facts, args.preview)

    out_w, out_h = (W // 2, H // 2) if args.preview else (W, H)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    writer = core.VideoWriter(args.out, out_w, out_h, FPS, crf=args.crf, preset="veryfast" if args.preview else "medium")
    if args.dump_frames:
        os.makedirs(args.dump_frames, exist_ok=True)

    timeline = {
        "fps": FPS, "facts": os.path.abspath(args.facts), "n_frames_total": N_FRAMES,
        "preview": args.preview, "frames": [], "events": [],
    }
    t_start = time.time()
    by_shot: dict[str, Shot] = {s.id: s for s in shots}
    cur = None
    for i, f in enumerate(frames):
        shot = next(s for s in shots if s.f0 <= f < s.f1)
        if shot is not cur:
            cur = shot
            print(f"[render] {shot.id} frames {shot.f0}-{shot.f1 - 1} ({shot.t0:.1f}-{shot.t1:.1f} s)")
        fn = resolve_scene(shot)
        ctx.shot = shot
        ctx.t = f / FPS
        img, state, events = fn(ctx, ctx.t - shot.t0, f)
        if not isinstance(img, Image.Image) or img.size != (W, H):
            raise ValueError(f"{shot.id} frame {f}: scene must return a {W}x{H} PIL image, got {getattr(img, 'size', None)}")
        if img.mode != "RGB":
            img = img.convert("RGB")
        if args.safe_zone:
            common.draw_safe_zone(img)
        out = img.resize((out_w, out_h), Image.LANCZOS) if args.preview else img
        writer.write(out)
        if args.dump_frames:
            out.save(os.path.join(args.dump_frames, f"f{f:04d}_{shot.id}.png"))
        state = state if isinstance(state, dict) and "osc" in state and "drone" in state else common.audio_state(**(state or {}))
        timeline["frames"].append({"frame": f, "t": ctx.t, "shot": shot.id, "audio": state})
        timeline["events"].extend(normalise_events(events, f))
        if (i + 1) % 30 == 0 or i == len(frames) - 1:
            el = time.time() - t_start
            print(f"[render] {i + 1}/{len(frames)} frames, {el:.1f} s, {(i + 1) / el:.1f} fps", flush=True)
    writer.close()
    os.makedirs(os.path.dirname(os.path.abspath(args.timeline)), exist_ok=True)
    with open(args.timeline, "w") as fh:
        json.dump(timeline, fh)
    log_path = os.path.splitext(args.timeline)[0] + "_shrinks.log"   # next to the timeline: partial renders never wipe the full film's log
    with open(log_path, "w") as fh:
        fh.write(f"# text shrinks of {args.out} (frames {frames[0]}-{frames[-1]}, facts {args.facts})\n")
        fh.write("\n".join(common.SHRINK_LOG) + ("\n" if common.SHRINK_LOG else ""))
    print(f"[render] wrote {args.out} ({writer.n} frames), timeline {args.timeline}, "
          f"{len(common.SHRINK_LOG)} text shrinks (see {log_path})")


if __name__ == "__main__":
    main()
