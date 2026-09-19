#!/usr/bin/env python3
"""Verifier's own pure-Python Langton's ant (dict grid), written from CONVENTIONS.md, with its own
splitmix64 sampler. Usage: python3 mypy_ant.py k p seed idx [extra_steps]  or  python3 mypy_ant.py empty
Prints onset s (= max{k: t[k]!=t[k+104]}), certification step, direction, bbox."""
import sys, json
M = (1 << 64) - 1
def cfg(k, p, seed, idx):
    s = (seed*0x9E3779B97F4A7C15 + idx*0xBF58476D1CE4E5B9 + k*0x94D049BB133111EB + int(round(1000*p))*0xD6E8FEB86659FD93) & M
    xmin = -(k // 2); out = set()
    for i in range(k*k):
        s = (s + 0x9E3779B97F4A7C15) & M; z = s
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M
        z ^= z >> 31
        if (z >> 11) / 2.0**53 < p: out.add((xmin + i % k, xmin + i // k))
    return out
def run(black, extra=3000):
    """Simulate until certified (then `extra` more steps to double-check periodicity persists)."""
    g = {c: 1 for c in black}
    x = y = d = 0; t = [None]; pos = [(0, 0)]
    bx0 = min([0] + [c[0] for c in black]); bx1 = max([0] + [c[0] for c in black])
    by0 = min([0] + [c[1] for c in black]); by1 = max([0] + [c[1] for c in black])
    bb = [(bx0, by0, bx1, by1)]
    L = 0; cert = None; n = 0; stop = None
    while True:
        n += 1
        c = g.get((x, y), 0)
        if c: d = (d - 1) % 4; t.append('L')      # black: left (counter-clockwise)
        else: d = (d + 1) % 4; t.append('R')      # white: right (clockwise)
        g[(x, y)] = 1 - c
        bx0 = min(bx0, x); bx1 = max(bx1, x); by0 = min(by0, y); by1 = max(by1, y)
        bb.append((bx0, by0, bx1, by1))
        if d == 0: y += 1
        elif d == 1: x += 1
        elif d == 2: y -= 1
        else: x -= 1
        pos.append((x, y))
        if n > 104 and t[n] != t[n-104]: L = n - 104
        if cert is None and n >= L + 2184:
            dx = x - pos[n-104][0]; dy = y - pos[n-104][1]
            if dx and dy:
                B = bb[L]
                ex = (x - B[2] >= 20) if dx > 0 else (B[0] - x >= 20)
                ey = (y - B[3] >= 20) if dy > 0 else (B[1] - y >= 20)
                if ex and ey: cert = n; disp = (dx, dy); stop = n + extra
        if stop is not None and n >= stop: break
        if n > 5_000_000: break
    s = 0
    for k in range(n - 104, 0, -1):
        if t[k] != t[k+104]: s = k; break
    mism = sum(1 for k in range(s+1, n-104+1) if t[k] != t[k+104])
    dirn = ('+x' if disp[0] > 0 else '-x') + ',' + ('+y' if disp[1] > 0 else '-y') if cert else None
    return {'onset_step': s, 'certification_step': cert, 'direction': dirn, 'disp': disp if cert else None, 'bbox_pre_onset': bb[s], 'steps_run': n, 'mismatches_after_s': mism, 'final_pos_at_cert': pos[cert] if cert else None}
if __name__ == '__main__':
    if sys.argv[1] == 'empty': r = run(set()); r['n_black'] = 0
    else:
        k, p, seed, idx = int(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
        extra = int(sys.argv[5]) if len(sys.argv) > 5 else 3000
        b = cfg(k, p, seed, idx); r = run(b, extra); r['n_black'] = len(b); r.update({'k': k, 'p': p, 'seed': seed, 'sample_index': idx})
    print(json.dumps(r))
