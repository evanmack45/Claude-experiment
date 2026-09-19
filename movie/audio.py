"""Audio engine for "Two Rules, One Road" (STORYBOARD section 4).

Driven ONLY by the timeline JSON that render.py writes:

    PYTHONPATH=. python3 audio.py --timeline build/timeline.json --wav build/audio.wav \
        [--mux build/video.mp4 --out build/final.mp4] [--target-lufs -14]

Per-frame state (timeline["frames"][i]["audio"], see SCENES_CONTRACT.md):
  osc   : [{"run", "step", "gain_db"}]  turn-stream oscillator voices (layer 1)
  pad   : {"chord", "cutoff", "detune_cents", "gain_db"} | None        (layer 3)
  drone : {"on", "gain_db", "add_e"}                                     (layer 3)
  noise : {"gain_db", "cutoff"} | None   filtered-noise shimmer (S11)
  mute  : bool                            hard silence (S06 16.0-16.4)
One-shot events (timeline["events"]): {"type", "frame", ...} - see HITS below.

Audio time = index of the frame in the timeline (partial renders stay in sync
with their clip).  Master: layers -> soft limiter -> loudness normalisation
to the target integrated loudness (measured with ffmpeg -af ebur128, RMS
fallback) -> true-peak limiter (-3.5 dBTP on the WAV, so the AAC stays <= -1 dBTP).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import tempfile

import numpy as np

import common
import core

SR = 48_000
SPF = SR // common.FPS            # 1600 samples per frame
OSR = 4 * SR                      # 192 kHz oscillator rate
OSPF = OSR // common.FPS          # 6400
HEAD_RATE = 22_880.0              # turns/s -> 104-periodic data = 220 Hz (A3)
HEAD2_RATE = 11_440.0             # 110 Hz copy at -9 dB
JUMP_BASE, JUMP_JITTER = 1600, 800
XFADE = int(0.006 * OSR)          # 6 ms equal-power crossfade
PERIOD = 104


def db(g: float) -> float:
    return 0.0 if g is None or g <= -200 else 10.0 ** (g / 20.0)


# --------------------------------------------------------------------------
# Notes and chords (STORYBOARD 4.3)
# --------------------------------------------------------------------------

def note_hz(name: str) -> float:
    m = re.fullmatch(r"([A-Ga-g])([#b]?)(-?\d)", name)
    if not m:
        raise ValueError(f"bad note name {name!r}")
    semis = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}[m.group(1).upper()]
    semis += {"#": 1, "b": -1, "": 0}[m.group(2)]
    octave = int(m.group(3))
    return 440.0 * 2 ** ((octave - 4) + semis / 12.0)


CHORDS = {
    "chaos": ["A2", "Bb3", "E4", "F4"],
    "highway": ["A2", "E3", "A3", "C#4", "E4"],
    "highway_shimmer": ["A2", "E3", "A3", "C#4", "E4", "A5", "E6"],
    "lone_a2": ["A2"],
    "rub": ["A2", "Bb2"],
    "climb_a2": ["A2"],
    "climb_cs3": ["C#3"],
    "climb_e3": ["E3"],
    "off": [],
}


def chord_notes(spec) -> list[str]:
    if spec is None:
        return []
    if isinstance(spec, str):
        if spec in CHORDS:
            return CHORDS[spec]
        return [spec]
    return [s if isinstance(s, str) else f"{float(s):.4f}Hz" for s in spec]


def spec_hz(name: str) -> float:
    return float(name[:-2]) if name.endswith("Hz") else note_hz(name)


# --------------------------------------------------------------------------
# DSP helpers
# --------------------------------------------------------------------------

def _onepole_kernel(fc: float, sr: int) -> np.ndarray:
    """Truncated impulse response of the one-pole lowpass y[n] = a x[n] + (1-a) y[n-1]."""
    alpha = (1.0 / sr) / (1.0 / (2 * math.pi * fc) + 1.0 / sr)
    decay = 1.0 - alpha
    n = int(min(8192, max(4, math.ceil(math.log(1e-4) / math.log(decay)))))
    return alpha * decay ** np.arange(n)


def lowpass(x: np.ndarray, fc: float, sr: int = SR) -> np.ndarray:
    """One-pole lowpass via FFT/direct convolution with a truncated kernel (fast for long signals)."""
    h = _onepole_kernel(fc, sr)
    if len(x) < 4 * len(h):
        return np.convolve(x, h)[: len(x)]
    n = 1 << int(math.ceil(math.log2(len(x) + len(h))))
    y = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(h, n), n)[: len(x)]
    return y


def highpass(x: np.ndarray, fc: float, sr: int = SR) -> np.ndarray:
    return x - lowpass(x, fc, sr)


def lowpass_varying(x: np.ndarray, fc_per_frame: np.ndarray, spf: int = SPF, sr: int = SR) -> np.ndarray:
    """One-pole lowpass whose cutoff changes per frame (overlap-add of per-frame kernels)."""
    out = np.zeros(len(x) + 8192)
    for i in range(0, len(x), spf):
        fi = min(i // spf, len(fc_per_frame) - 1)
        fc = float(fc_per_frame[fi])
        if fc <= 0:
            continue
        seg = x[i: i + spf]
        y = np.convolve(seg, _onepole_kernel(fc, sr))
        out[i: i + len(y)] += y
    return out[: len(x)]


def per_sample(values_per_frame: np.ndarray, spf: int = SPF) -> np.ndarray:
    """Linear interpolation of per-frame values (at frame centres) to per-sample values."""
    n = len(values_per_frame)
    centres = (np.arange(n) + 0.5) * spf
    return np.interp(np.arange(n * spf), centres, values_per_frame)


def smooth_frames(values: np.ndarray, attack_frames: float, release_frames: float) -> np.ndarray:
    """Asymmetric one-pole on a per-frame series (fast attack, slow release)."""
    out = np.empty_like(values, dtype=np.float64)
    ka = 1.0 - math.exp(-1.0 / max(1e-6, attack_frames))
    kr = 1.0 - math.exp(-1.0 / max(1e-6, release_frames))
    v = float(values[0])
    for i, tgt in enumerate(values):
        v += (tgt - v) * (ka if tgt > v else kr)
        out[i] = v
    return out


def osc_phase(freq_per_sample: np.ndarray, sr: int = SR) -> np.ndarray:
    return 2 * np.pi * np.cumsum(freq_per_sample) / sr


# --------------------------------------------------------------------------
# Layer 1 - turn-stream oscillator
# --------------------------------------------------------------------------

class TurnStream:
    """Sonifies one run's turn array with two read heads (22,880 and 11,440 turns/s)."""

    def __init__(self, w: np.ndarray, rng: np.random.Generator):
        self.w = w
        self.rng = rng
        self.heads = [None, None]         # float head indices
        self.gain = 0.0
        self.mult = 1.0                   # current read-head rate multiplier

    def _render(self, H: float, rate: float, n: int) -> tuple[np.ndarray, float]:
        idx = np.floor(H + (rate / OSR) * np.arange(n)).astype(np.int64)
        if idx[-1] >= len(self.w) or idx[0] < 0:     # a too-short run would drone on a held value
            raise RuntimeError(f"turn-stream head at {idx[-1]} past the end of a {len(self.w)}-turn run")
        return self.w[idx].astype(np.float64), H + (rate / OSR) * n

    def _head_chunk(self, hi: int, rate: float, step: int) -> np.ndarray:
        H = self.heads[hi]
        jump_from = None
        if H is None:
            H = float(step)
        else:
            j = self.rng.integers(0, JUMP_JITTER + 1)
            if H < step or H - step > JUMP_BASE + j:
                jump_from = H
                H = step + ((H - step) % PERIOD)
        chunk, H_end = self._render(H, rate, OSPF)
        if jump_from is not None:
            old, _ = self._render(jump_from, rate, XFADE)
            t = np.linspace(0, 1, XFADE, endpoint=False)
            chunk[:XFADE] = old * np.cos(t * np.pi / 2) + chunk[:XFADE] * np.sin(t * np.pi / 2)
        self.heads[hi] = H_end
        return chunk

    def frame(self, step: int | None, gain: float, rate_mult: float = 1.0) -> np.ndarray:
        """192 kHz chunk for one frame. step=None -> voice inactive (fade to 0).  `rate_mult`
        scales both read-head rates (2.0 = one octave up: 104-periodic data sounds at 440 Hz)."""
        if step is None:
            if self.gain <= 0:
                return None
            chunk = np.zeros(OSPF)
            if self.heads[0] is not None:
                c1, _ = self._render(self.heads[0], HEAD_RATE * self.mult, OSPF)
                c2, _ = self._render(self.heads[1], HEAD2_RATE * self.mult, OSPF)
                chunk = c1 + db(-9) * c2
            ramp = np.linspace(self.gain, 0.0, OSPF)
            self.gain = 0.0
            self.heads = [None, None]
            return chunk * ramp
        self.mult = float(rate_mult)
        c1 = self._head_chunk(0, HEAD_RATE * self.mult, step)
        c2 = self._head_chunk(1, HEAD2_RATE * self.mult, step)
        ramp = np.linspace(self.gain, gain, OSPF)
        self.gain = gain
        return (c1 + db(-9) * c2) * ramp


def render_oscillator(frames: list[dict], cache: common.RunCache, seed: int = 20260919) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = len(frames)
    out = np.zeros(n * OSPF)
    voices: dict[str, TurnStream] = {}
    for i, fr in enumerate(frames):
        active = {v["run"]: v for v in fr["audio"].get("osc", [])}
        for rid in set(voices) | set(active):
            if rid not in voices:
                w = cache.turns(rid).astype(np.int8) * 2 - 1
                voices[rid] = TurnStream(w, rng)
            v = active.get(rid)
            chunk = voices[rid].frame(int(v["step"]) if v else None, db(v["gain_db"]) if v else 0.0,
                                      float(v.get("rate_mult", 1.0)) if v else 1.0)
            if chunk is not None:
                out[i * OSPF: (i + 1) * OSPF] += chunk
    # decimate 4:1 with a box filter, then the 6 kHz lowpass
    y = out.reshape(-1, 4).mean(axis=1)
    return lowpass(y, 6000.0)


# --------------------------------------------------------------------------
# Layer 3 - drone and pad
# --------------------------------------------------------------------------

def render_drone(frames: list[dict]) -> np.ndarray:
    n = len(frames)
    on = np.array([db(f["audio"]["drone"]["gain_db"]) if f["audio"]["drone"]["on"] else 0.0 for f in frames])
    add_e = np.array([1.0 if f["audio"]["drone"].get("add_e") else 0.0 for f in frames])
    g = per_sample(smooth_frames(on, 3, 6))
    ge = per_sample(smooth_frames(add_e, 6, 12))
    t = np.arange(n * SPF) / SR
    cents = 3.0 * np.sin(2 * np.pi * 0.1 * t)
    det = 2 ** (cents / 1200.0)
    y = np.sin(osc_phase(55.0 * det)) + 0.7 * np.sin(osc_phase(110.0 / det))
    y += 0.6 * ge * np.sin(osc_phase(82.4 * det))
    return y * g / 1.7


def render_pad(frames: list[dict]) -> np.ndarray:
    """Four detuned voices per note, per-frame chord gains (40 ms attack, 400 ms release),
    detune drift in cents, time-varying one-pole lowpass. Returns (n, 2) stereo."""
    n = len(frames)
    notes_per_frame = [chord_notes(f["audio"]["pad"]["chord"]) if f["audio"]["pad"] else [] for f in frames]
    all_notes = sorted({nm for lst in notes_per_frame for nm in lst}, key=spec_hz)
    if not all_notes:
        return np.zeros((n * SPF, 2))
    gain = np.array([db(f["audio"]["pad"]["gain_db"]) if f["audio"]["pad"] else 0.0 for f in frames])
    cutoff = np.array([f["audio"]["pad"]["cutoff"] if f["audio"]["pad"] else 1200.0 for f in frames])
    cents = np.array([f["audio"]["pad"]["detune_cents"] if f["audio"]["pad"] else 0.0 for f in frames])
    cents_s = per_sample(cents)
    out = np.zeros((n * SPF, 2))
    detunes = (-0.004, -0.0013, 0.0013, 0.004)
    for nm in all_notes:
        present = np.array([1.0 if nm in lst else 0.0 for lst in notes_per_frame])
        env = per_sample(smooth_frames(present, 1.2, 12.0))
        if env.max() <= 1e-6:
            continue
        f0 = spec_hz(nm)
        sig = np.zeros((n * SPF, 2))
        for vi, d in enumerate(detunes):
            freq = f0 * (1 + d) * 2 ** ((cents_s if vi % 2 else 0.0) / 1200.0)
            ph = osc_phase(freq)
            saw = 2 * ((ph / (2 * np.pi)) % 1.0) - 1
            v = 0.35 * saw + 0.65 * np.sin(ph)
            pan = 0.65 if vi % 2 == 0 else 0.35
            sig[:, 0] += v * pan
            sig[:, 1] += v * (1 - pan)
        out += sig * env[:, None] / 4.0
    g = per_sample(smooth_frames(gain, 3, 9)) / 1.5
    for ch in range(2):
        out[:, ch] = lowpass_varying(out[:, ch], cutoff) * g
    return out


def render_noise(frames: list[dict], rng: np.random.Generator) -> np.ndarray:
    n = len(frames)
    gain = np.array([db(f["audio"]["noise"]["gain_db"]) if f["audio"].get("noise") else 0.0 for f in frames])
    if gain.max() <= 0:
        return np.zeros(n * SPF)
    cutoff = np.array([f["audio"]["noise"]["cutoff"] if f["audio"].get("noise") else 2000.0 for f in frames])
    x = rng.standard_normal(n * SPF) * 0.3
    return lowpass_varying(x, cutoff) * per_sample(smooth_frames(gain, 2, 6))


# --------------------------------------------------------------------------
# Layers 2 + 4 - plucks and hits (STORYBOARD 4.2, 4.4)
# --------------------------------------------------------------------------

CLICK_GAIN = 0.2   # bare clicks / click clusters (3 ms noise bursts have a high true-peak ratio)


def _t(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def g_click(dur: float = 0.003, rng=None) -> np.ndarray:
    rng = rng or np.random.default_rng(1)
    x = rng.standard_normal(int(dur * SR)) * np.hanning(int(dur * SR))
    return highpass(lowpass(x, 6000.0), 1500.0) * 2.0


def g_pluck(turn: str, rng=None) -> np.ndarray:
    f = 329.63 if turn == "R" else 220.0
    t = _t(0.35)
    y = np.sin(2 * np.pi * f * t) + db(-6) * np.sin(2 * np.pi * 2 * f * t) + db(-12) * np.sin(2 * np.pi * 3 * f * t)
    y *= core.adsr(len(t), 0.003, 0.120, 0.3, 0.230)
    core.place(y, 0, g_click(rng=rng), 0.5)
    return y * 0.5


def g_thump(dur: float = 0.25, tail: float | None = None) -> np.ndarray:
    length = tail if tail else dur
    t = _t(length)
    env = np.exp(-t / (length / 5.0))
    return np.sin(2 * np.pi * 48.0 * t) * env * db(-8) * 1.5


def g_kick() -> np.ndarray:
    t = _t(0.12)
    f = 48.0 + 60.0 * np.exp(-t / 0.02)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.03) * 0.8


def g_bell(freq: float = 880.0, decay: float = 2.0) -> np.ndarray:
    t = _t(decay)
    y = np.sin(2 * np.pi * freq * t) + db(-12) * np.sin(2 * np.pi * 2.0 * freq * t) + db(-18) * np.sin(2 * np.pi * 2.76 * freq * t)
    return y * np.exp(-t / (decay / 4.0)) * 0.35


def g_blip(freq: float, dur: float = 0.3) -> np.ndarray:
    t = _t(dur)
    return np.sin(2 * np.pi * freq * t) * core.adsr(len(t), 0.005, 0.1, 0.4, 0.15) * 0.3


def g_knock() -> np.ndarray:
    t = _t(0.06)
    return np.sin(2 * np.pi * 150.0 * t) * np.exp(-t / 0.012) * 0.7


def g_click_cluster(rng) -> np.ndarray:
    y = np.zeros(int(0.06 * SR))
    for i in range(5):
        core.place(y, int(i * 0.010 * SR), g_click(rng=rng), CLICK_GAIN)
    return y


def g_riser(dur: float = 3.0, rng=None) -> np.ndarray:
    """White noise through a band-pass sweeping 200 Hz -> 8 kHz over `dur` s (-24 dBFS)."""
    rng = rng or np.random.default_rng(2)
    n = int(dur * SR)
    x = rng.standard_normal(n)
    frames = int(math.ceil(n / SPF))
    u = np.arange(frames) / max(1, frames - 1)
    fc = 200.0 * (8000.0 / 200.0) ** u
    y = lowpass_varying(x, fc * 1.5) - lowpass_varying(x, fc / 1.5)
    return y * np.linspace(0.3, 1.0, n) * db(-24) * 4.0


def g_chord_hit() -> np.ndarray:
    t = _t(1.5)
    y = np.zeros_like(t)
    for nm in ("A3", "C#4", "E4", "A4"):
        f = note_hz(nm)
        y += np.sin(2 * np.pi * f * t) + 0.2 * (2 * ((f * t) % 1) - 1)
    return lowpass(y, 2500.0) * np.exp(-t / 0.4) * 0.1


def g_micro_tick() -> np.ndarray:
    t = _t(0.0015)
    return np.sin(2 * np.pi * 4000.0 * t) * np.hanning(len(t)) * 0.25


def g_slot_click() -> np.ndarray:
    t = _t(0.02)
    return lowpass(np.sign(np.sin(2 * np.pi * 900.0 * t)) * np.exp(-t / 0.004), 2000.0) * 0.5


def g_tick() -> np.ndarray:
    t = _t(0.008)
    return np.sin(2 * np.pi * 2000.0 * t) * np.hanning(len(t)) * 0.3


def g_thud() -> np.ndarray:
    t = _t(0.08)
    return lowpass(np.sin(2 * np.pi * 120.0 * t) * np.exp(-t / 0.02), 400.0) * 0.5


def render_events(events: list[dict], frame_index: dict[int, int], n_frames: int, cache: common.RunCache) -> np.ndarray:
    """Place every one-shot event at its frame (events on unrendered frames are dropped)."""
    rng = np.random.default_rng(7)
    out = np.zeros(n_frames * SPF + 3 * SR)
    ticks_this_second: dict[int, int] = {}
    for ev in events:
        f = int(ev["frame"])
        if f not in frame_index:
            continue
        s = frame_index[f] * SPF
        typ = ev["type"]
        if typ == "thump":
            core.place(out, s, g_thump())
        elif typ == "thump_long":
            core.place(out, s, g_thump(tail=float(ev.get("tail", 2.0))))
        elif typ == "kick":
            core.place(out, s, g_kick())
        elif typ == "pluck":
            turn = ev.get("turn")
            if turn is None:
                turn = "R" if int(cache.turns(ev["run"])[int(ev["step"]) - 1]) == 1 else "L"
            core.place(out, s, g_pluck(turn, rng), db(float(ev.get("gain_db", 0.0))))
        elif typ == "click":
            core.place(out, s, g_click(rng=rng), CLICK_GAIN)
        elif typ == "click_cluster":
            core.place(out, s, g_click_cluster(rng))
        elif typ == "knock":
            core.place(out, s, g_knock())
        elif typ == "bell":
            core.place(out, s, g_bell(float(ev.get("freq", 880.0)), float(ev.get("decay", 2.0))))
        elif typ == "blip":
            freq = float(ev["freq"]) if "freq" in ev else note_hz(ev.get("note", "A4"))
            core.place(out, s, g_blip(freq))
        elif typ == "riser":
            core.place(out, s, g_riser(float(ev.get("dur", 3.0)), rng))
        elif typ == "chord_hit":
            core.place(out, s, g_chord_hit())
        elif typ == "micro_tick":
            sec = f // common.FPS
            budget = 200 - ticks_this_second.get(sec, 0)
            per_frame = 7 if f % 3 == 2 else 6                      # 6, 6, 7 -> 190/s, never above 200/s
            k = int(min(int(ev.get("n", 1)), max(0, budget), per_frame))
            ticks_this_second[sec] = ticks_this_second.get(sec, 0) + k
            for i in range(k):
                core.place(out, s + int(i * SPF / max(1, k)), g_micro_tick())
        elif typ == "slot_click":
            core.place(out, s, g_slot_click())
        elif typ == "tick":
            core.place(out, s, g_tick())
        elif typ == "thud":
            core.place(out, s, g_thud())
        else:
            raise ValueError(f"unknown audio event type {typ!r} at frame {f}")
    return out[: n_frames * SPF]


# --------------------------------------------------------------------------
# Master
# --------------------------------------------------------------------------

def soft_limit(x: np.ndarray, knee: float = 0.5) -> np.ndarray:
    a = np.abs(x)
    over = a > knee
    y = x.copy()
    y[over] = np.sign(x[over]) * (knee + (1 - knee) * np.tanh((a[over] - knee) / (1 - knee)))
    return y


def _oa_convolve(x: np.ndarray, h: np.ndarray, block: int = 1 << 18) -> np.ndarray:
    """Overlap-add FFT convolution (same length as x, kernel centred: delay len(h)//2 removed)."""
    n, m = len(x), len(h)
    nfft = 1 << int(math.ceil(math.log2(block + m)))
    Hf = np.fft.rfft(h, nfft)
    out = np.zeros(n + m)
    for s in range(0, n, block):
        seg = x[s: s + block]
        out[s: s + len(seg) + m - 1] += np.fft.irfft(np.fft.rfft(seg, nfft) * Hf, nfft)[: len(seg) + m - 1]
    return out[m // 2: m // 2 + n]


def true_peak_envelope(stereo: np.ndarray, os_factor: int = 4) -> np.ndarray:
    """Per-sample inter-sample peak estimate: |4x windowed-sinc upsampled signal|, max over
    both channels and the 4 sub-samples (ITU-R BS.1770 style)."""
    half = 24
    n = 2 * half * os_factor + 1
    t = (np.arange(n) - half * os_factor) / os_factor
    h = np.sinc(t) * np.kaiser(n, 8.0)
    peak = np.zeros(len(stereo))
    for ch in range(stereo.shape[1]):
        up = np.zeros(len(stereo) * os_factor)
        up[::os_factor] = stereo[:, ch]
        y = np.abs(_oa_convolve(up, h)).reshape(len(stereo), os_factor).max(axis=1)
        np.maximum(peak, y, out=peak)
    return peak


def _windowed_min(v: np.ndarray, radius: int) -> np.ndarray:
    out = v.copy()
    for k in range(1, radius + 1):
        out[k:] = np.minimum(out[k:], v[:-k])
        out[:-k] = np.minimum(out[:-k], v[k:])
    return out


def true_peak_limit(stereo: np.ndarray, ceiling_db: float = -3.5, block: int = 48, release_s: float = 0.08) -> np.ndarray:
    """Linked-stereo true-peak limiter: gain = ceiling / inter-sample peak, held per 1 ms block
    with a +-1 block lookahead window and an exponential release; interpolated per sample so no
    block ever exceeds its required gain (a 1 ms gain ramp is inaudible on the short hits)."""
    ceiling = db(ceiling_db)
    env = true_peak_envelope(stereo)
    n = len(env)
    nb = int(math.ceil(n / block))
    padded = np.full(nb * block, 0.0)
    padded[:n] = env
    g_block = np.minimum(1.0, ceiling / np.maximum(padded.reshape(nb, block).max(axis=1), 1e-9))
    g_block = _windowed_min(g_block, 1)
    kr = 1.0 - math.exp(-block / (release_s * SR))
    g = np.empty(nb)
    cur = 1.0
    for i in range(nb):                       # release smoothing (111k blocks for the full film)
        cur = min(g_block[i], cur + (1.0 - cur) * kr)
        g[i] = cur
    centres = (np.arange(nb) + 0.5) * block
    gs = np.interp(np.arange(n), centres, g)
    return stereo * gs[:, None]


def measure_lufs(wav_path: str) -> float | None:
    """Integrated loudness via ffmpeg -af ebur128 (None if unavailable)."""
    try:
        res = subprocess.run([core.ffmpeg_exe(), "-hide_banner", "-nostats", "-i", wav_path, "-af", "ebur128", "-f", "null", "-"],
                             capture_output=True, text=True, timeout=600)
    except Exception:
        return None
    m = re.findall(r"I:\s+(-?[\d.]+)\s+LUFS", res.stderr)
    return float(m[-1]) if m else None


def measure_true_peak(wav_path: str) -> float | None:
    try:
        res = subprocess.run([core.ffmpeg_exe(), "-hide_banner", "-nostats", "-i", wav_path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                             capture_output=True, text=True, timeout=600)
    except Exception:
        return None
    m = re.findall(r"Peak:\s+(-?[\d.]+)\s+dBFS", res.stderr)
    return float(m[-1]) if m else None


def normalise(stereo: np.ndarray, target_lufs: float, ceiling_dbtp: float = -3.5,
              work_dir: str = common.BUILD_DIR) -> tuple[np.ndarray, dict]:
    """Master chain: soft limiter -> gain iterated on ffmpeg's ebur128 integrated loudness
    (RMS approximation only as a fallback) -> true-peak limiter at `ceiling_dbtp` (default
    -3.5 dBTP: the AAC encode overshoots by 1-1.5 dB, so the mp4 stays under the -1 dBTP spec) ->
    a final ffmpeg true-peak measurement with a global trim if the limiter's estimate was short."""
    info = {}
    y = soft_limit(stereo)
    os.makedirs(work_dir, exist_ok=True)                      # a fresh clone has no build/ yet
    fd, tmp = tempfile.mkstemp(prefix="_loudness_probe_", suffix=".wav", dir=work_dir)
    os.close(fd)                                              # per-process name: concurrent runs never clobber each other

    def loudness(sig):
        core.write_wav(tmp, sig)
        lufs = measure_lufs(tmp)
        if lufs is None:
            rms = math.sqrt(np.mean(sig ** 2)) or 1e-9
            info["method"] = "rms-approx"
            return 20 * math.log10(rms) - 0.7  # RMS approximation of K-weighted loudness
        info["method"] = "ffmpeg-ebur128"
        return lufs

    for it in range(4):
        peak = np.max(np.abs(y)) or 1.0
        if peak > 0.98:
            y = y / peak * 0.98
        lufs = loudness(y)
        info[f"pass{it}_lufs"] = lufs
        delta = target_lufs - lufs
        if abs(delta) < 0.3:
            break
        y = soft_limit(y * db(delta))
    for it in range(3):                       # limiter -> measure; trim globally if still over
        y = true_peak_limit(y, ceiling_dbtp)
        lufs = loudness(y)
        tp = measure_true_peak(tmp)
        info[f"limit{it}_lufs"], info[f"limit{it}_true_peak_dbtp"] = lufs, tp
        if tp is not None and tp > ceiling_dbtp + 0.2:
            y = y * db(ceiling_dbtp - tp)
            continue
        if abs(target_lufs - lufs) > 0.5 and it < 2:
            y = y * db(target_lufs - lufs)
            continue
        break
    lufs = loudness(y)                        # measure the signal actually written, after any trim
    tp = measure_true_peak(tmp)
    info["lufs"], info["true_peak_dbtp"] = lufs, tp
    if os.path.exists(tmp):
        os.remove(tmp)
    return y, info


def build(timeline: dict, facts_path: str | None = None) -> tuple[np.ndarray, dict]:
    frames = timeline["frames"]
    n = len(frames)
    facts = common.load_facts(facts_path or timeline["facts"])
    cache = common.RunCache(facts)
    frame_index = {int(fr["frame"]): i for i, fr in enumerate(frames)}
    rng = np.random.default_rng(11)
    print(f"[audio] {n} frames ({n / common.FPS:.1f} s)")
    osc = render_oscillator(frames, cache)
    print("[audio] oscillator done")
    drone = render_drone(frames)
    pad = render_pad(frames)
    print("[audio] drone + pad done")
    noise = render_noise(frames, rng)
    hits = render_events(timeline["events"], frame_index, n, cache)
    print(f"[audio] {len(timeline['events'])} events placed")
    mono = osc + drone + noise + hits
    stereo = np.stack([mono, mono], axis=1) + pad
    mute = np.array([0.0 if fr["audio"].get("mute") else 1.0 for fr in frames])
    m = np.repeat(mute, SPF)
    k = int(0.003 * SR)
    m = np.convolve(m, np.ones(k) / k, mode="same")
    stereo *= m[:, None]
    return stereo, {"layers_peak": {"osc": float(np.abs(osc).max()), "drone": float(np.abs(drone).max()),
                                    "pad": float(np.abs(pad).max()), "hits": float(np.abs(hits).max())}}


def probe_file(path: str) -> str:
    ff = core.ffmpeg_exe()
    ffprobe = core.ffprobe_exe()
    lines = [f"size: {os.path.getsize(path) / 1e6:.2f} MB"]
    if ffprobe:
        out = subprocess.run([ffprobe, "-v", "error", "-show_entries",
                              "stream=codec_name,width,height,r_frame_rate,nb_frames,pix_fmt,sample_rate,channels,bit_rate:format=duration",
                              "-of", "default=noprint_wrappers=1", path], capture_output=True, text=True).stdout
        lines.append(out.strip())
    else:  # the imageio-ffmpeg bundle ships no ffprobe: parse `ffmpeg -i`
        info = subprocess.run([ff, "-hide_banner", "-i", path], capture_output=True, text=True).stderr
        lines.extend(l.strip() for l in info.splitlines() if "Stream #" in l or "Duration:" in l)
    res = subprocess.run([ff, "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True)
    tail = res.stderr[res.stderr.rfind("Integrated loudness"):] if "Integrated loudness" in res.stderr else res.stderr[-600:]
    lines.append(tail.strip())
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--timeline", default=os.path.join(common.BUILD_DIR, "timeline.json"))
    ap.add_argument("--wav", default=os.path.join(common.BUILD_DIR, "audio.wav"))
    ap.add_argument("--facts", help="override the facts path stored in the timeline")
    ap.add_argument("--target-lufs", type=float, default=-14.0)
    ap.add_argument("--ceiling", type=float, default=-3.5, help="true-peak ceiling of the WAV in dBTP (the AAC encode overshoots by ~1-1.5 dB)")
    ap.add_argument("--mux", metavar="VIDEO", help="silent video from render.py to mux with")
    ap.add_argument("--out", metavar="MP4", help="final muxed file (with --mux)")
    args = ap.parse_args(argv)

    with open(args.timeline) as fh:
        timeline = json.load(fh)
    stereo, info = build(timeline, args.facts)
    stereo, norm = normalise(stereo, args.target_lufs, args.ceiling)
    info.update(norm)
    os.makedirs(os.path.dirname(os.path.abspath(args.wav)), exist_ok=True)
    core.write_wav(args.wav, stereo)
    print(f"[audio] wrote {args.wav}: {json.dumps(info)}")
    if args.mux:
        out = args.out or os.path.splitext(args.mux)[0] + "_final.mp4"
        core.mux_audio(args.mux, args.wav, out)
        print(f"[audio] muxed -> {out}")
        print(probe_file(out))


if __name__ == "__main__":
    main()
