"""Core primitives for rendering the Langton's Ant movie.

Everything here is deliberately dependency-light: numpy + Pillow for frames,
the imageio-ffmpeg bundled ffmpeg for encoding, numpy for audio synthesis.

Coordinate conventions follow research/CONVENTIONS.md:
  - grid cells (x, y) with y increasing NORTH (up on screen)
  - ant starts at (0, 0) facing North; on white turn right, on black turn left,
    flip, move.
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import wave
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# --------------------------------------------------------------------------
# ffmpeg
# --------------------------------------------------------------------------

def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # pragma: no cover
        return "ffmpeg"


def ffprobe_exe() -> str | None:
    """An ffprobe next to the bundled ffmpeg (basename only: the imageio_ffmpeg directory name
    must not be rewritten), else one on PATH, else None (callers parse `ffmpeg -i`)."""
    ff = ffmpeg_exe()
    cand = os.path.join(os.path.dirname(ff), os.path.basename(ff).replace("ffmpeg", "ffprobe", 1))
    if os.path.exists(cand):
        return cand
    return shutil.which("ffprobe")


# --------------------------------------------------------------------------
# Simulation
# --------------------------------------------------------------------------

# N, E, S, W as (dx, dy); right turn = +1 (mod 4), left turn = -1
DIRS = np.array([[0, 1], [1, 0], [0, -1], [-1, 0]], dtype=np.int64)


@dataclass
class AntRun:
    """A fully recorded run of the ant.

    pos[k] is the ant position AFTER k steps (pos[0] = origin).
    dir[k] is the ant heading AFTER k steps (0=N,1=E,2=S,3=W).
    turns[k-1] is 'R'/'L' for step k (k = 1..n).  Stored as uint8: 1=R, 0=L.
    grid is the final grid as a (size, size) uint8 array; cell (x, y) lives at
    grid[y + off, x + off].  visited counts how many times each cell was
    stepped on (useful for tinting).
    """

    size: int
    off: int
    pos: np.ndarray
    dir: np.ndarray
    turns: np.ndarray
    grid: np.ndarray
    visited: np.ndarray
    initial_black: list[tuple[int, int]] = field(default_factory=list)

    def cell(self, x: int, y: int) -> int:
        return int(self.grid[y + self.off, x + self.off])


def simulate(n_steps: int, initial_black=(), size: int = 1024) -> AntRun:
    """Run the ant for n_steps from the given initial black cells.

    Returns an AntRun holding the trajectory and final grid.  Also records
    a per-step snapshot capability via `grid_at` (see below) by keeping the
    flip list, so the renderer can reconstruct any intermediate grid cheaply.
    """
    off = size // 2
    grid = np.zeros((size, size), dtype=np.uint8)
    visited = np.zeros((size, size), dtype=np.int32)
    for (x, y) in initial_black:
        grid[y + off, x + off] = 1
    pos = np.zeros((n_steps + 1, 2), dtype=np.int64)
    dirs = np.zeros(n_steps + 1, dtype=np.int8)
    turns = np.zeros(n_steps, dtype=np.uint8)
    x, y, d = 0, 0, 0
    for k in range(n_steps):
        gy, gx = y + off, x + off
        c = grid[gy, gx]
        if c == 0:
            d = (d + 1) & 3
            turns[k] = 1
            grid[gy, gx] = 1
        else:
            d = (d - 1) & 3
            turns[k] = 0
            grid[gy, gx] = 0
        visited[gy, gx] += 1
        dx, dy = DIRS[d]
        x += int(dx)
        y += int(dy)
        pos[k + 1] = (x, y)
        dirs[k + 1] = d
        if not (1 <= gx + dx < size - 1 and 1 <= gy + dy < size - 1):
            raise RuntimeError(f"ant left the {size}x{size} grid at step {k+1}")
    return AntRun(size, off, pos, dirs, turns, grid, visited, list(initial_black))


class GridPlayer:
    """Replays a run step by step, keeping the grid state at an arbitrary step.

    Because each step flips exactly the cell the ant stands on, the grid at
    step k is determined by the initial grid plus flips of pos[0..k-1].
    We keep a current state and move forward/backward as needed.
    """

    def __init__(self, run: AntRun):
        self.run = run
        self.size = run.size
        self.off = run.off
        self.grid = np.zeros((run.size, run.size), dtype=np.uint8)
        self.visited = np.zeros((run.size, run.size), dtype=np.uint8)
        self.age = np.zeros((run.size, run.size), dtype=np.int32)  # step of last flip
        for (x, y) in run.initial_black:
            self.grid[y + self.off, x + self.off] = 1
        self.k = 0

    def _flip(self, k: int):
        x, y = self.run.pos[k]
        gy, gx = int(y) + self.off, int(x) + self.off
        self.grid[gy, gx] ^= 1
        self.visited[gy, gx] = 1
        self.age[gy, gx] = k

    def seek(self, k: int):
        k = max(0, min(k, len(self.run.turns)))
        while self.k < k:
            self._flip(self.k)
            self.k += 1
        while self.k > k:
            self.k -= 1
            self._flip(self.k)  # flipping is an involution

    @property
    def ant_xy(self):
        x, y = self.run.pos[self.k]
        return int(x), int(y)

    @property
    def ant_dir(self) -> int:
        return int(self.run.dir[self.k])


def find_onset(turns: np.ndarray, period: int = 104, min_periods: int = 20) -> int:
    """Smallest s such that turns[k] == turns[k+period] for all k >= s (0-based),
    given at least min_periods of periodicity at the tail.  Returns -1 if the
    tail is not periodic.  Mirrors CONVENTIONS.md (s = steps completed before
    the periodic regime; turns index k here corresponds to step k+1)."""
    n = len(turns)
    if n < period * (min_periods + 1):
        return -1
    eq = turns[:-period] == turns[period:]
    # eq[k] True means step k+1 and k+1+period agree
    if not eq[-period * min_periods:].all():
        return -1
    # walk back from the end to find the first False
    bad = np.nonzero(~eq)[0]
    return int(bad[-1] + 1) if len(bad) else 0


# --------------------------------------------------------------------------
# Easing / timing helpers
# --------------------------------------------------------------------------

def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def smoothstep(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_in_out_cubic(t):
    t = clamp(t)
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in_cubic(t):
    t = clamp(t)
    return t * t * t


def lerp(a, b, t):
    return a + (b - a) * t


def fade(t, t0, t1, fin=0.4, fout=0.4):
    """Opacity 0..1 for something living on [t0, t1] with fade in/out."""
    if t < t0 or t > t1:
        return 0.0
    a = clamp((t - t0) / fin) if fin > 0 else 1.0
    b = clamp((t1 - t) / fout) if fout > 0 else 1.0
    return min(a, b)


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def hex_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


@dataclass
class Camera:
    cx: float  # cell coordinates of the frame centre
    cy: float
    cells_across: float  # number of cells spanning the frame width


def render_grid(
    grid: np.ndarray,
    off: int,
    cam: Camera,
    W: int,
    H: int,
    palette: dict,
    visited: np.ndarray | None = None,
    age: np.ndarray | None = None,
    k: int | None = None,
    gap: bool = True,
) -> Image.Image:
    """Render the grid to a W x H RGB image using camera `cam`.

    palette keys: bg, white, black, visited (optional tint for visited white cells),
    each as (r, g, b).  When zoomed in (cell >= 6 px) and gap=True, a 1px
    darker gap is drawn between cells so the lattice reads as cells.
    """
    cell_px = W / cam.cells_across
    # region of the grid that is visible (in cell coords)
    x0 = cam.cx - cam.cells_across / 2
    y_top = cam.cy + (H / cell_px) / 2
    # integer cell window with a margin
    ix0 = int(math.floor(x0)) - 1
    ix1 = int(math.ceil(x0 + cam.cells_across)) + 2
    iy1 = int(math.ceil(y_top)) + 2  # north-most
    iy0 = int(math.floor(y_top - H / cell_px)) - 1
    gx0, gx1 = ix0 + off, ix1 + off
    gy0, gy1 = iy0 + off, iy1 + off
    size = grid.shape[0]
    gx0c, gx1c = max(0, gx0), min(size, gx1)
    gy0c, gy1c = max(0, gy0), min(size, gy1)
    sub = grid[gy0c:gy1c, gx0c:gx1c]
    # colour classes: 0 = untouched white, 1 = black, 2 = visited white
    cls = sub.astype(np.uint8).copy()
    if visited is not None:
        vsub = visited[gy0c:gy1c, gx0c:gx1c]
        cls[(sub == 0) & (vsub > 0)] = 2
    lut = np.array(
        [palette.get("white", (255, 255, 255)), palette.get("black", (0, 0, 0)), palette.get("visited", palette.get("white", (255, 255, 255)))],
        dtype=np.uint8,
    )
    rgb = lut[cls]  # (h, w, 3)
    # pad to the full window if the window exceeds the grid
    padh = (gy0c - gy0, gy1 - gy1c)
    padw = (gx0c - gx0, gx1 - gx1c)
    if any(padh) or any(padw):
        rgb = np.pad(rgb, (padh, padw, (0, 0)), mode="constant", constant_values=0)
        bgc = np.array(palette.get("bg", (0, 0, 0)), dtype=np.uint8)
        mask = np.ones(rgb.shape[:2], dtype=bool)
        mask[padh[0] : rgb.shape[0] - padh[1], padw[0] : rgb.shape[1] - padw[1]] = False
        rgb[mask] = bgc
    # rows in rgb go from iy0 (south) to iy1 (north); screen wants north at top
    rgb = rgb[::-1]
    img = Image.fromarray(np.ascontiguousarray(rgb), "RGB")
    # affine: output pixel (px, py) -> input pixel (u, v)
    #   u = (px / cell_px + x0 - ix0)
    #   v = ((py / cell_px) + (iy1 - y_top))     (input row 0 is north-most = iy1)
    a = 1.0 / cell_px
    c = x0 - ix0
    f = iy1 - y_top
    if cell_px >= 1.0:
        resample = Image.NEAREST
        out = img.transform((W, H), Image.AFFINE, (a, 0, c, 0, a, f), resample=resample)
    else:
        # zoomed out: box-downsample first for anti-aliasing
        factor = int(math.ceil(1.0 / cell_px))
        small = img.resize((max(1, img.width // factor), max(1, img.height // factor)), Image.BOX)
        a2 = a / factor
        out = small.transform((W, H), Image.AFFINE, (a2, 0, c / factor, 0, a2, f / factor), resample=Image.BILINEAR)
    if gap and cell_px >= 6:
        # draw subtle grid lines between cells
        arr = np.array(out)
        gap_col = np.array(palette.get("gap", palette.get("bg", (0, 0, 0))), dtype=np.uint8)
        xs = ((np.arange(0, cam.cells_across + 3) - c) * cell_px).astype(int)
        xs = xs[(xs >= 0) & (xs < W)]
        ys = ((np.arange(0, H / cell_px + 3) - f) * cell_px).astype(int)
        ys = ys[(ys >= 0) & (ys < H)]
        arr[:, xs] = gap_col
        arr[ys, :] = gap_col
        out = Image.fromarray(arr, "RGB")
    return out


def cell_to_px(cam: Camera, W: int, H: int, x: float, y: float):
    """Map cell coordinates (centre of cell x,y is (x+0.5, y+0.5)) to pixel coords."""
    cell_px = W / cam.cells_across
    px = (x - (cam.cx - cam.cells_across / 2)) * cell_px
    y_top = cam.cy + (H / cell_px) / 2
    py = (y_top - y) * cell_px
    return px, py


def draw_ant(img: Image.Image, cam: Camera, x: int, y: int, d: int, color, glow=None, min_px=10):
    """Draw the ant as a heading-triangle inside cell (x, y), with an optional glow."""
    W, H = img.size
    cell_px = W / cam.cells_across
    px, py = cell_to_px(cam, W, H, x + 0.5, y + 0.5)  # centre of the cell
    r = max(min_px, cell_px * 0.45)
    if glow is not None:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(layer)
        for i, alpha in ((3.0, 40), (2.2, 70), (1.5, 110)):
            dl.ellipse([px - r * i, py - r * i, px + r * i, py + r * i], fill=(*glow, alpha))
        img.paste(layer, (0, 0), layer)
    draw = ImageDraw.Draw(img)
    ang = {0: -90, 1: 0, 2: 90, 3: 180}[d]  # screen angle in degrees (y down)
    pts = []
    for a_off in (0, 140, 220):
        a = math.radians(ang + a_off)
        rr = r if a_off == 0 else r * 0.9
        pts.append((px + rr * math.cos(a), py + rr * math.sin(a)))
    draw.polygon(pts, fill=color)
    return img


# --------------------------------------------------------------------------
# Text
# --------------------------------------------------------------------------

# Font discovery: DejaVu (and Liberation) TTFs are searched in the usual Linux/macOS/Windows
# font directories, in $LANGTON_FONT_DIR, and in matplotlib's bundled copy of DejaVu if that
# package happens to be installed.  Set LANGTON_FONT_DIR to a directory holding the .ttf files
# (any layout; the search is recursive) when none of the defaults apply.
_FONT_FILES = {
    "bold": "DejaVuSans-Bold.ttf",
    "regular": "DejaVuSans.ttf",
    "mono": "DejaVuSansMono.ttf",
    "monobold": "DejaVuSansMono-Bold.ttf",
    "serif": "DejaVuSerif-Bold.ttf",
    "liberation-bold": "LiberationSans-Bold.ttf",
    "liberation": "LiberationSans-Regular.ttf",
}
_FONT_SEARCH_DIRS = [
    os.environ.get("LANGTON_FONT_DIR", ""),
    "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation", "/usr/share/fonts/truetype",
    "/usr/share/fonts/dejavu", "/usr/share/fonts/TTF", "/usr/share/fonts", "/usr/local/share/fonts",
    os.path.expanduser("~/.fonts"), os.path.expanduser("~/.local/share/fonts"),
    os.path.expanduser("~/Library/Fonts"), "/Library/Fonts", "/System/Library/Fonts", "/opt/homebrew/share/fonts",
    "C:/Windows/Fonts",
]
_font_cache: dict = {}
_font_paths: dict = {}


def _matplotlib_font_dir():
    try:
        import matplotlib  # type: ignore

        return os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
    except Exception:
        return ""


def find_font_file(basename: str) -> str:
    """Absolute path of a font file found by name in the search directories (recursive)."""
    if basename in _font_paths:
        return _font_paths[basename]
    dirs = [d for d in _FONT_SEARCH_DIRS if d] + [_matplotlib_font_dir()]
    for d in dirs:
        if not d or not os.path.isdir(d):
            continue
        direct = os.path.join(d, basename)
        if os.path.exists(direct):
            _font_paths[basename] = direct
            return direct
        for root, _dirs, files in os.walk(d):
            if basename in files:
                _font_paths[basename] = os.path.join(root, basename)
                return _font_paths[basename]
    raise FileNotFoundError(
        f"font {basename} not found; install the DejaVu fonts (package fonts-dejavu / dejavu-fonts) or set "
        f"LANGTON_FONT_DIR to a directory containing it. Searched: {', '.join(d for d in dirs if d)}")


# Backwards-compatible view: FONTS[name] resolves lazily to the discovered path.
class _FontTable(dict):
    def __missing__(self, name):
        if name in _FONT_FILES:
            return find_font_file(_FONT_FILES[name])
        raise KeyError(name)

    def get(self, name, default=None):
        try:
            return self[name]
        except (KeyError, FileNotFoundError):
            return default


FONTS = _FontTable()


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    key = (name, size)
    if key not in _font_cache:
        path = FONTS.get(name, None) or name
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt, max_width: int) -> list[str]:
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for w in words:
            trial = (cur + " " + w).strip()
            if draw.textlength(trial, font=fnt) <= max_width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def draw_text_block(
    img: Image.Image,
    text: str,
    fnt,
    color,
    y: float,
    x_center: float | None = None,
    max_width: int | None = None,
    opacity: float = 1.0,
    line_spacing: float = 1.15,
    align: str = "center",
    x_left: float | None = None,
    shadow=(0, 0, 0),
    shadow_opacity: float = 0.75,
    shadow_offset: int = 3,
    box=None,
) -> float:
    """Draw (possibly multi-line, wrapped) text with fade opacity.  Returns the y
    just below the block.  `box`, if given, is (fill_rgb, pad, alpha) for a
    rounded backing panel behind the text."""
    if opacity <= 0:
        return y
    W, H = img.size
    if x_center is None:
        x_center = W / 2
    if max_width is None:
        max_width = int(W * 0.86)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    lines = wrap_text(d, text, fnt, max_width)
    ascent, descent = fnt.getmetrics()
    lh = (ascent + descent) * line_spacing
    total_h = lh * len(lines)
    if box is not None:
        fill, pad, balpha = box
        widths = [d.textlength(l, font=fnt) for l in lines]
        bw = max(widths) + 2 * pad
        bx0 = (x_center - bw / 2) if align == "center" else (x_left - pad)
        d.rounded_rectangle([bx0, y - pad, bx0 + bw, y + total_h + pad], radius=pad, fill=(*fill, int(balpha * 255 * opacity)))
    a = int(255 * clamp(opacity))
    for i, line in enumerate(lines):
        ly = y + i * lh
        if align == "center":
            lw = d.textlength(line, font=fnt)
            lx = x_center - lw / 2
        else:
            lx = x_left if x_left is not None else W * 0.07
        if shadow is not None and shadow_opacity > 0:
            d.text((lx + shadow_offset, ly + shadow_offset), line, font=fnt, fill=(*shadow, int(a * shadow_opacity)))
        d.text((lx, ly), line, font=fnt, fill=(*color, a))
    img.paste(layer, (0, 0), layer)
    return y + total_h


def draw_rect(img, box, fill, opacity=1.0, radius=0):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(box, radius=radius, fill=(*fill, int(255 * clamp(opacity))))
    img.paste(layer, (0, 0), layer)
    return img


def vignette(img: Image.Image, strength: float = 0.35, color=(0, 0, 0)) -> Image.Image:
    """Darken the edges slightly so text reads better on busy grids."""
    W, H = img.size
    key = ("vig", W, H, round(strength, 3))
    mask = _font_cache.get(key)
    if mask is None:
        yy, xx = np.mgrid[0:H, 0:W]
        rx = (xx - W / 2) / (W / 2)
        ry = (yy - H / 2) / (H / 2)
        rr = np.sqrt(rx * rx + ry * ry) / math.sqrt(2)
        m = np.clip((rr - 0.45) / 0.55, 0, 1) ** 1.6 * strength
        mask = Image.fromarray((m * 255).astype(np.uint8), "L")
        _font_cache[key] = mask
    dark = Image.new("RGB", img.size, color)
    return Image.composite(dark, img, mask)


# --------------------------------------------------------------------------
# Video writer
# --------------------------------------------------------------------------

class VideoWriter:
    def __init__(self, path: str, W: int, H: int, fps: int = 30, crf: int = 18, preset: str = "medium"):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.W, self.H = W, H
        self.n = 0
        cmd = [
            ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(crf), "-preset", preset,
            "-profile:v", "high", "-level", "4.1", "-movflags", "+faststart", path,
        ]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def write(self, img: Image.Image):
        assert img.size == (self.W, self.H), img.size
        if img.mode != "RGB":
            img = img.convert("RGB")
        self.proc.stdin.write(img.tobytes())
        self.n += 1

    def close(self):
        self.proc.stdin.close()
        rc = self.proc.wait()
        if rc != 0:
            raise RuntimeError(f"ffmpeg exited with {rc}")


def mux_audio(video_path: str, wav_path: str, out_path: str, bitrate: str = "192k"):
    cmd = [
        ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
        "-i", video_path, "-i", wav_path,
        "-c:v", "copy", "-c:a", "aac", "-b:a", bitrate, "-ar", "48000", "-shortest",
        "-movflags", "+faststart", out_path,
    ]
    subprocess.run(cmd, check=True)


# --------------------------------------------------------------------------
# Audio synthesis
# --------------------------------------------------------------------------

SR = 48000


def write_wav(path: str, audio: np.ndarray, sr: int = SR):
    """audio: float array (n,) or (n, 2) in [-1, 1]."""
    a = np.asarray(audio, dtype=np.float64)
    if a.ndim == 1:
        a = np.stack([a, a], axis=1)
    peak = np.max(np.abs(a)) if a.size else 0.0
    if peak > 0.98:
        a = a / peak * 0.98
    pcm = (a * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def adsr(n: int, a: float, d: float, s: float, r: float, sr: int = SR) -> np.ndarray:
    """Envelope of n samples with attack/decay/release in seconds and sustain level."""
    env = np.ones(n)
    na, nd, nr = int(a * sr), int(d * sr), int(r * sr)
    na = min(na, n)
    env[:na] = np.linspace(0, 1, na, endpoint=False)
    if nd > 0 and na + nd <= n:
        env[na : na + nd] = np.linspace(1, s, nd, endpoint=False)
        env[na + nd :] = s
    if nr > 0:
        nr = min(nr, n)
        env[-nr:] *= np.linspace(1, 0, nr)
    return env


def tone(freq: float, dur: float, sr: int = SR, wave_="sine", detune=0.0) -> np.ndarray:
    n = int(dur * sr)
    t = np.arange(n) / sr
    if wave_ == "sine":
        y = np.sin(2 * np.pi * freq * t)
    elif wave_ == "tri":
        y = 2 * np.abs(2 * ((t * freq) % 1) - 1) - 1
    elif wave_ == "saw":
        y = 2 * ((t * freq) % 1) - 1
    elif wave_ == "square":
        y = np.sign(np.sin(2 * np.pi * freq * t))
    else:
        raise ValueError(wave_)
    if detune:
        y = 0.5 * (y + np.sin(2 * np.pi * freq * (1 + detune) * t))
    return y


def lowpass(x: np.ndarray, cutoff: float, sr: int = SR) -> np.ndarray:
    """One-pole lowpass (cheap, stable)."""
    rc = 1.0 / (2 * np.pi * cutoff)
    dt = 1.0 / sr
    alpha = dt / (rc + dt)
    y = np.empty_like(x)
    acc = 0.0
    # vectorised via lfilter-free recursion in chunks
    # (pure python loop over 48k*90 samples is too slow, so use scipy-free trick)
    b = np.array([alpha])
    a = 1 - alpha
    # Use cumulative formulation: y[n] = alpha*x[n] + (1-alpha)*y[n-1]
    # => y[n] = sum_k alpha*(1-alpha)^(n-k) x[k]; compute with exp weights in blocks
    n = len(x)
    block = 4096
    for s in range(0, n, block):
        xb = x[s : s + block]
        m = len(xb)
        w = a ** np.arange(m)
        # y_b[i] = a^(i+1)*acc + alpha * sum_{k<=i} a^(i-k) x[k]
        conv = np.convolve(xb, w * alpha)[:m]
        yb = (a ** np.arange(1, m + 1)) * acc + conv
        y[s : s + m] = yb
        acc = yb[-1]
    return y


def place(buffer: np.ndarray, start_sample: int, grain: np.ndarray, gain: float = 1.0):
    """Add grain into buffer at start_sample (clipped to bounds)."""
    n = len(buffer)
    s = start_sample
    e = s + len(grain)
    if s >= n or e <= 0:
        return
    gs = 0 if s >= 0 else -s
    ge = len(grain) if e <= n else len(grain) - (e - n)
    buffer[max(0, s) : min(n, e)] += gain * grain[gs:ge]


def pad_chord(freqs, dur, sr=SR, gain=0.2, attack=1.5, release=2.0, cutoff=1200.0):
    n = int(dur * sr)
    out = np.zeros(n)
    for f in freqs:
        out += tone(f, dur, sr, "saw", detune=0.004) * 0.35 + tone(f, dur, sr, "sine") * 0.65
    out = lowpass(out, cutoff, sr)
    out *= adsr(n, attack, 0.0, 1.0, release, sr) * gain / max(1, len(freqs))
    return out


def probe(path: str) -> dict:
    """Return basic stream info using ffprobe if available, else ffmpeg -i parsing."""
    ff = ffmpeg_exe()
    ffprobe = ffprobe_exe()
    if ffprobe:
        out = subprocess.run([ffprobe, "-v", "error", "-show_entries", "stream=codec_name,width,height,r_frame_rate,duration,pix_fmt,sample_rate,channels", "-of", "default=noprint_wrappers=1", path], capture_output=True, text=True).stdout
        return {"raw": out}
    out = subprocess.run([ff, "-i", path], capture_output=True, text=True).stderr
    return {"raw": out}
