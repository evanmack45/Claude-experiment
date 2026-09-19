#!/usr/bin/env python3
"""Pure-Python reference (verify/adversarial): python3 pyref.py <cfgfile|-> N
Simulates N steps per CONVENTIONS.md, prints onset s (max k<=N-104 with t[k]!=t[k+104]),
first certification step (20 periods + escape margin 20 beyond bbox of origin+initial+cells read in steps 1..s),
direction, contact step."""
import sys, re, json
cfg, N = sys.argv[1], int(sys.argv[2])
txt = '' if cfg == '-' else re.sub(r'#.*', '', open(cfg).read())
v = [int(a) for a in re.findall(r'[-+]?\d+', txt)]
init = set(zip(v[0::2], v[1::2])); black = set(init)
DX = [0, 1, 0, -1]; DY = [1, 0, -1, 0]   # N E S W
x = y = 0; d = 0; t = [None]; pos = [(0, 0)]; contact = 0
for k in range(1, N + 1):
    if (x, y) in black:
        d = (d - 1) % 4; black.remove((x, y)); t.append('L')
        if not contact and (x, y) in init: contact = k
    else:
        d = (d + 1) % 4; black.add((x, y)); t.append('R')
    x += DX[d]; y += DY[d]; pos.append((x, y))
s = 0
for k in range(1, N - 104 + 1):
    if t[k] != t[k + 104]: s = k
cert = None; direction = None
if N - 104 - s >= 2080:
    cells = list(init) + pos[:max(s, 1)]   # pos[0..s-1] = cells read in steps 1..s, plus origin
    bx0 = min(c[0] for c in cells); bx1 = max(c[0] for c in cells); by0 = min(c[1] for c in cells); by1 = max(c[1] for c in cells)
    for m in range(s + 2184, N + 1):
        ddx = pos[m][0] - pos[m - 104][0]; ddy = pos[m][1] - pos[m - 104][1]
        if ddx == 0 or ddy == 0: continue
        okx = pos[m][0] >= bx1 + 20 if ddx > 0 else pos[m][0] <= bx0 - 20
        oky = pos[m][1] >= by1 + 20 if ddy > 0 else pos[m][1] <= by0 - 20
        if okx and oky:
            cert = m; direction = ('+x' if ddx > 0 else '-x') + ',' + ('+y' if ddy > 0 else '-y'); break
print(json.dumps(dict(onset=s, cert_step=cert, direction=direction, contact=contact, N=N)))
