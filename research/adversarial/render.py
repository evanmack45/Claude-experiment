#!/usr/bin/env python3
"""Render the final grid of a configuration (black cells at the certification step, ant trail
coloured by time) to a PNG.  Usage: python3 render.py <cfgfile> <out.png> [scale]"""
import sys, re, json, subprocess, os
import numpy as np
from PIL import Image
cfg, outpng = sys.argv[1], sys.argv[2]; scale = int(sys.argv[3]) if len(sys.argv) > 3 else 4
here = os.path.dirname(os.path.abspath(__file__))
r = json.loads(subprocess.run([os.path.join(here, 'antsim'), 'run', cfg], capture_output=True, text=True).stdout)
N = r['cert_step'] if r['cert_step'] > 0 else r['steps_simulated']
ints = [int(v) for v in re.findall(r'[-+]?\d+', re.sub(r'#.*', '', open(cfg).read()))]
init = set(zip(ints[0::2], ints[1::2])); black = set(init)
DX = [0, 1, 0, -1]; DY = [1, 0, -1, 0]; x = y = d = 0; last = {}
for k in range(1, N + 1):
    if (x, y) in black: d = (d + 3) % 4; black.discard((x, y))
    else: d = (d + 1) % 4; black.add((x, y))
    last[(x, y)] = k; x += DX[d]; y += DY[d]
x0, y0, x1, y1 = r['bbox_all']; W, H = x1 - x0 + 3, y1 - y0 + 3
img = np.full((H, W, 3), 245, np.uint8)
for (cx, cy), k in last.items():
    f = k / N; col = np.array([int(40 + 200 * f), int(60 + 120 * (1 - f)), int(220 - 180 * f)])
    img[y1 + 1 - cy, cx - x0 + 1] = col if (cx, cy) not in black else col // 2
for cx, cy in init: img[y1 + 1 - cy, cx - x0 + 1] = (230, 30, 30)
Image.fromarray(img).resize((W * scale, H * scale), Image.NEAREST).save(outpng)
print(json.dumps(dict(onset=r['onset_step'], cert_step=N, bbox=r['bbox_all'], png=outpng, size=[W * scale, H * scale])))
