#!/usr/bin/env python3
"""Independent pure-Python cross-check of antsim (research/CONVENTIONS.md).
Usage: python3 verify_py.py <cfgfile> <nsteps>
Simulates nsteps, prints onset s = max{k: t[k]!=t[k+104]} over the simulated range,
direction of the last period and the number of full periods verified. Exits 1 if
antsim (run with the same cfg) disagrees on the onset step / direction."""
import sys, json, re, subprocess, os
cfg, N = sys.argv[1], int(sys.argv[2])
ints = [int(v) for v in re.findall(r'[-+]?\d+', re.sub(r'#.*', '', open(cfg).read()))]
black = set(zip(ints[0::2], ints[1::2]))
DX = [0, 1, 0, -1]; DY = [1, 0, -1, 0]
x = y = d = 0; t = []; pos = [(0, 0)]
for k in range(1, N + 1):
    c = (x, y) in black
    if c: d = (d + 3) % 4; black.discard((x, y)); t.append('L')
    else: d = (d + 1) % 4; black.add((x, y)); t.append('R')
    x += DX[d]; y += DY[d]; pos.append((x, y))
s = 0
for k in range(1, N - 104 + 1):
    if t[k - 1] != t[k + 104 - 1]: s = k
dx = pos[N][0] - pos[N - 104][0]; dy = pos[N][1] - pos[N - 104][1]
direction = ('+x' if dx > 0 else '-x') + ',' + ('+y' if dy > 0 else '-y')
periods = (N - 104 - s) // 104
print(json.dumps({"python_onset": s, "python_direction": direction, "disp": [dx, dy], "periods_verified": periods, "steps": N}))
here = os.path.dirname(os.path.abspath(__file__))
r = json.loads(subprocess.run([os.path.join(here, 'antsim'), 'run', cfg], capture_output=True, text=True).stdout)
ok = (r['onset_step'] == s and r['direction'] == direction and r['cert_step'] <= N)
print("antsim:", r['onset_step'], r['direction'], "cert_step", r['cert_step'], "->", "AGREE" if ok else "DISAGREE")
sys.exit(0 if ok else 1)
