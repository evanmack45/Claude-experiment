#!/usr/bin/env python3
"""literal.py -- my own deliberately literal pure-Python simulation of CONVENTIONS.md
(written independently of research/exhaustive/naive.py).

Simulates N steps from a list of initial black cells, keeps the whole turn string,
then applies the definitions literally:
  s      = smallest s>=0 with t[k]==t[k+104] for all k in s+1 .. N-104   (== max mismatch index)
  cert   = first n >= s+2184 (20 periods verified: k in s+1..n-104) such that the ant's
           position after step n is >= 20 cells beyond the onset bounding box in both
           coordinates in the direction of travel (sign of pos[n]-pos[n-104]).
  Two bounding boxes are reported: 'bbox_incl_init' = cells modified in steps 1..s plus
  origin plus ALL initial black cells (finder's conservative reading) and 'bbox_modified'
  = cells modified in steps 1..s plus origin only (literal reading).
Usage: python3 literal.py N [x,y ...]
"""
import sys
P = 104

def sim(black, N):
    g = {c: 1 for c in black}
    x = y = 0; d = 0
    mv = ((0, 1), (1, 0), (0, -1), (-1, 0))   # N, E, S, W
    t = [None]; pos = [(0, 0)]
    for n in range(1, N + 1):
        c = g.get((x, y), 0)
        if c == 1:
            d = (d - 1) % 4; t.append('L'); g[(x, y)] = 0
        else:
            d = (d + 1) % 4; t.append('R'); g[(x, y)] = 1
        x += mv[d][0]; y += mv[d][1]
        pos.append((x, y))
    return t, pos

def onset(t):
    N = len(t) - 1
    s = 0
    for k in range(N - P, 0, -1):
        if t[k] != t[k + P]:
            s = k; break
    # cross-check with the "smallest s" phrasing
    assert all(t[k] == t[k + P] for k in range(s + 1, N - P + 1))
    assert s == 0 or t[s] != t[s + P]
    return s

def bbox(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))

def cert_step(pos, s, bb, N):
    for n in range(s + P + 20 * P, N + 1):
        dx = pos[n][0] - pos[n - P][0]; dy = pos[n][1] - pos[n - P][1]
        if dx == 0 or dy == 0: continue
        okx = pos[n][0] >= bb[2] + 20 if dx > 0 else pos[n][0] <= bb[0] - 20
        oky = pos[n][1] >= bb[3] + 20 if dy > 0 else pos[n][1] <= bb[1] - 20
        if okx and oky:
            return n, (dx, dy)
    return None, None

def analyse(black, N):
    t, pos = sim(black, N)
    s = onset(t)
    modified = pos[:s] + [(0, 0)]              # cell modified at step k is pos[k-1]
    bb_mod = bbox(modified)
    bb_incl = bbox(modified + list(black))
    c_incl, disp = cert_step(pos, s, bb_incl, N)
    c_mod, disp2 = cert_step(pos, s, bb_mod, N)
    res = dict(N=N, s=s, cert_incl_init=c_incl, cert_modified_only=c_mod, disp=disp,
               direction=None if disp is None else ("+x" if disp[0] > 0 else "-x") + "," + ("+y" if disp[1] > 0 else "-y"),
               bbox_incl_init=bb_incl, bbox_modified=bb_mod, first_turns="".join(t[1:11]),
               periods_verified=(N - P - s) // P)
    if c_incl:
        n = c_incl
        xs = [pos[q][0] for q in range(n - P, n + 1)]; ys = [pos[q][1] for q in range(n - P, n + 1)]
        res["footprint_last_period_wh"] = (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
        res["footprint_extent_dxdy"] = (max(xs) - min(xs), max(ys) - min(ys))
        res["pos_at_cert"] = pos[n]
    res["max_abs_coord_over_path"] = max(max(abs(p[0]), abs(p[1])) for p in pos)
    return res

if __name__ == "__main__":
    N = int(sys.argv[1])
    black = [tuple(int(v) for v in a.split(",")) for a in sys.argv[2:]]
    r = analyse(black, N)
    print("black=%s" % black)
    for k, v in r.items(): print("%s = %s" % (k, v))
