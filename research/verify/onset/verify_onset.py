#!/usr/bin/env python3
"""Independent re-derivation of every claim in research/results/onset.json.
Written from CONVENTIONS.md only (not copied from research/onset/).
Usage: python3 verify_onset.py N
Simulates N steps of Langton's Ant from the empty grid with a dict grid,
then recomputes onset, certification, highway, and pre-onset statistics.
"""
import sys, math, json, collections
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
P = 104

# CONVENTIONS: N=(0,+1) -> E=(+1,0) -> S=(0,-1) -> W=(-1,0) is a right turn (clockwise).
DIRS = [(0, 1), (1, 0), (0, -1), (-1, 0)]   # index 0=N,1=E,2=S,3=W ; right = +1
grid = collections.defaultdict(int)
x, y, d = 0, 0, 0
pos = [(0, 0)]          # pos[k] = position after k steps
dirs = [0]              # dirs[k] = direction after k steps
t = ['?']               # t[k] = turn at step k
black_at = {}
for k in range(1, N + 1):
    c = grid[(x, y)]
    if c == 0:
        d = (d + 1) % 4; t.append('R')
    else:
        d = (d - 1) % 4; t.append('L')
    grid[(x, y)] = 1 - c
    x += DIRS[d][0]; y += DIRS[d][1]
    pos.append((x, y)); dirs.append(d)
tstr = ''.join(t)

# ---- onset: smallest s>=0 with t[k]==t[k+104] for all k>=s+1 (within k+104<=N) ----
s = 0
for k in range(N - P, 0, -1):
    if t[k] != t[k + P]:
        s = k; break
print("N", N)
print("onset_s", s, "t[s]", t[s], "t[s+104]", t[s + P])
mism = sum(1 for k in range(s + 1, N - P + 1) if t[k] != t[k + P])
print("mismatches_after_s", mism)
print("periods_verified (N-104-s)//104", (N - P - s) // P)
# alternative: smallest s' with t[k]==t[k+104] for all k>=s'  => s'=s+1
print("alt_onset_inclusive", s + 1)
# state periodicity: smallest k with pos[j+P]-pos[j] const and dirs[j+P]==dirs[j] for all j>=k
D = (pos[N][0] - pos[N - P][0], pos[N][1] - pos[N - P][1])
s_state = 0
for j in range(N - P, -1, -1):
    if (pos[j + P][0] - pos[j][0], pos[j + P][1] - pos[j][1]) != D or dirs[j + P] != dirs[j]:
        s_state = j + 1; break
print("s_state", s_state, "D", D)
# displacement for every period start j in [s, N-P]
disps = set((pos[j + P][0] - pos[j][0], pos[j + P][1] - pos[j][1]) for j in range(s, N - P + 1))
print("disp_set", disps)

# ---- pre-onset sets ----
# cell read/flipped at step k is pos[k-1]. modified before step s+1 = steps 1..s -> pos[0..s-1]
mod = set(pos[:s])
vis = set(pos[:s + 1])
xs = [p[0] for p in mod]; ys = [p[1] for p in mod]
minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
print("n_modified_pre", len(mod), "n_visited_0..s", len(vis))
print("bbox_mod", minx, maxx, miny, maxy, "size", maxx - minx + 1, maxy - miny + 1)
vxs = [p[0] for p in vis]; vys = [p[1] for p in vis]
print("bbox_vis", min(vxs), max(vxs), min(vys), max(vys))
print("ant_at_s", pos[s], "NESW"[dirs[s]])
# black cells at s: recount by replay
def black_after(n):
    g = collections.defaultdict(int); xx = yy = 0; dd = 0
    for k in range(1, n + 1):
        c = g[(xx, yy)]
        dd = (dd + 1) % 4 if c == 0 else (dd - 1) % 4
        g[(xx, yy)] = 1 - c
        xx += DIRS[dd][0]; yy += DIRS[dd][1]
    return {p for p, v in g.items() if v}
B_s = black_after(s); B_1040 = black_after(s + 1040); B_2080 = black_after(s + 2080)
print("black_at_s", len(B_s), "s+1040", len(B_1040), "s+2080", len(B_2080))
# distance stats over steps 0..s
maxr2 = -1; argmax = None; maxcheb = 0; maxman = 0
for k in range(s + 1):
    px, py = pos[k]
    r2 = px * px + py * py
    if r2 > maxr2: maxr2 = r2; argmax = k
    maxcheb = max(maxcheb, abs(px), abs(py)); maxman = max(maxman, abs(px) + abs(py))
print("max_euclid", "%.6f" % math.sqrt(maxr2), "argmax_step", argmax, "r2", maxr2, "cheb", maxcheb, "man", maxman)
# is the argmax unique?
ties = [k for k in range(s + 1) if pos[k][0]**2 + pos[k][1]**2 == maxr2]
print("argmax_ties", ties)
# last step reading a pre-onset-modified cell: cell read at step k is pos[k-1]
last_old = max(k for k in range(1, N + 1) if pos[k - 1] in mod)
print("last_step_reading_pre_onset_cell", last_old)

# ---- escape margin (travel direction -x,-y): margin = min(minx - x, miny - y) ----
sx = 1 if D[0] > 0 else -1; sy = 1 if D[1] > 0 else -1
def margin(k):
    px, py = pos[k]
    mx = (px - maxx) if sx > 0 else (minx - px)
    my = (py - maxy) if sy > 0 else (miny - py)
    return mx, my
mm = [min(margin(k)) for k in range(s, N + 1)]
m1 = s + next(i for i, v in enumerate(mm) if v >= 1)
m20_first = s + next(i for i, v in enumerate(mm) if v >= 20)
suf = mm[:]
for i in range(len(suf) - 2, -1, -1): suf[i] = min(suf[i], suf[i + 1])
m20_perm = s + next(i for i, v in enumerate(suf) if v >= 20)
print("first_outside_bbox_margin1", m1, "m20_first", m20_first, "m20_permanent", m20_perm, "margin_at_perm", margin(m20_perm))
ppm = [min(mm[i:i + P]) for i in range(0, len(mm) - P + 1, P)]
diffs = set(b - a for a, b in zip(ppm, ppm[1:]))
print("per_period_min_margin first 5", ppm[:5], "diff set", diffs, "n_periods", len(ppm))
print("never touches mod after m20_perm", all(pos[k] not in mod for k in range(m20_perm, N + 1)))
print("last step at which ant position is in bbox:", max(k for k in range(N + 1) if minx <= pos[k][0] <= maxx and miny <= pos[k][1] <= maxy))

# ---- highway ----
ps = tstr[s + 1: s + 1 + P]
print("turn_string_104", ps, "R", ps.count('R'), "L", ps.count('L'))
# check the same 104-string at every period start
print("period string same for all period starts:", all(tstr[j:j + P] == ps for j in range(s + 1, N - P + 1, P)))
offs_by_start = {}
for jj in range(s, N - P + 1, P):
    o = frozenset((pos[j][0] - pos[jj][0], pos[j][1] - pos[jj][1]) for j in range(jj, jj + P))
    offs_by_start.setdefault(o, []).append(jj)
print("n_distinct_offset_sets over all period starts", len(offs_by_start))
offs = sorted(max(offs_by_start, key=lambda o: len(offs_by_start[o])))
print("n_offsets", len(offs), "dx", min(o[0] for o in offs), max(o[0] for o in offs), "dy", min(o[1] for o in offs), max(o[1] for o in offs))
perp = [sx * dx - sy * dy for dx, dy in offs]
print("perp range (sx*dx - sy*dy)", min(perp), max(perp), "n lines", max(perp) - min(perp) + 1)
# alternative perp definition x+y (for direction (-1,-1), perpendicular is (1,-1): coordinate dx-dy)
perp2 = [dx - dy for dx, dy in offs]
print("perp range dx-dy", min(perp2), max(perp2), "n", max(perp2) - min(perp2) + 1)
print("period offsets", offs)
print("black per period from counts", (len(B_1040) - len(B_s)) / 10, (len(B_2080) - len(B_1040)) / 10, "R-L", ps.count('R') - ps.count('L'))
# trail black offsets: canonicalize black cells in the along-window [-60,-20) relative to ant at s+2080
xa, ya = pos[s + 2080]
canon = collections.Counter()
win = 0
for (bx, by) in B_2080:
    a = sx * (bx - xa) + sy * (by - ya)
    if -60 <= a < -20:
        win += 1
        kk = (a + 24) // 4
        canon[(bx - xa - kk * D[0], by - ya - kk * D[1])] += 1
print("window cells", win, "canon", sorted(canon.items()))
print("trail perp lines", sorted(set(sx * dx - sy * dy for dx, dy in canon)))
# JSON-able summary
json.dump({"N": N, "s": s, "mismatches": mism, "s_state": s_state, "D": D, "bbox": [minx, maxx, miny, maxy],
           "n_mod": len(mod), "black_s": len(B_s), "black_1040": len(B_1040), "black_2080": len(B_2080),
           "m1": m1, "m20_first": m20_first, "m20_perm": m20_perm, "last_old": last_old,
           "turn_string": ps, "offsets": offs, "argmax": argmax, "maxr2": maxr2,
           "pos_s": pos[s], "dir_s": "NESW"[dirs[s]]},
          open(f"/home/user/Claude-experiment/research/verify/onset/my_{N}.json", "w"), indent=1)
# dump my turn string for diffing against the finder's
open(f"/home/user/Claude-experiment/research/verify/onset/my_turns_{N}.txt", "w").write(tstr[1:] + "\n")
