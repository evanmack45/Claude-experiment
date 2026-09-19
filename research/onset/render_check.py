#!/usr/bin/env python3
"""Sanity PNG of the grid at step s and s+2080 (black cells + ant), for eyeballing. Usage: render_check.py OUTDIR RESDIR"""
import sys, json
from PIL import Image
out, res = sys.argv[1], sys.argv[2]
t = json.load(open(f"{res}/onset_trajectory.json"))
for name, cells, k in (("s", t["black_cells_at_s"], t["onset_step_s"]), ("s2080", t["black_cells_at_s_plus_2080"], t["onset_step_s"] + 2080)):
    xs = [c[0] for c in cells]; ys = [c[1] for c in cells]
    x0, x1, y0, y1 = min(xs) - 3, max(xs) + 3, min(ys) - 3, max(ys) + 3
    S = 6
    im = Image.new("RGB", ((x1 - x0 + 1) * S, (y1 - y0 + 1) * S), (255, 255, 255))
    px = im.load()
    def paint(x, y, col):
        for i in range(S):
            for j in range(S):
                px[(x - x0) * S + i, (y1 - y) * S + j] = col     # y up = north
    for x, y in cells: paint(x, y, (0, 0, 0))
    ax, ay, ad = t["ant_xyd_after_step"][k]
    paint(ax, ay, (220, 30, 30))
    im.save(f"{out}/grid_{name}.png")
    print(f"wrote {out}/grid_{name}.png  ({x0}..{x1}) x ({y0}..{y1}), ant at ({ax},{ay}) dir {ad}")
