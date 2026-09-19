#!/usr/bin/env python3
"""Independent re-derivation of every number claimed by research/onset (code review tests).

Independent simulator: complex-number heading (1j = North), set-of-black-cells grid,
forward-scan onset finder (different algorithm from ant.c's backward scan).
Usage: python3 review_tests.py [N]      (default N=200000; compares against research/onset/out and results/onset.json)
"""
import sys, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ONSET = os.path.join(HERE, '..', '..', 'onset')
RES = os.path.join(HERE, '..', '..', 'results')
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
P = 104
fails = []
def check(name, got, exp):
    ok = got == exp
    print(f"[{'OK ' if ok else 'FAIL'}] {name}: got {got!r} expected {exp!r}")
    if not ok: fails.append(name)

# ---------- independent simulation ----------
black = set()
pos = 0 + 0j; head = 1j            # facing North = +y
traj = [pos]; heads = [head]; t = ['?']
for k in range(1, N + 1):
    if pos in black:               # black -> left (counter-clockwise) = multiply by +i
        head *= 1j; t.append('L'); black.remove(pos)
    else:                          # white -> right (clockwise) = multiply by -i
        head *= -1j; t.append('R'); black.add(pos)
    pos += head
    traj.append(pos); heads.append(head)
DIRCODE = {1j: 0, 1: 1, -1j: 2, -1: 3}   # N E S W
xy = [(int(p.real), int(p.imag)) for p in traj]
dcode = [DIRCODE[h] for h in heads]

# ---------- 0. hand-checked first steps (CONVENTIONS worked by hand) ----------
check("hand: first 5 positions", xy[:6], [(0,0),(1,0),(1,-1),(0,-1),(0,0),(-1,0)])
check("hand: first 5 turns", ''.join(t[1:6]), "RRRRL")
check("hand: dir after step 1 is E", dcode[1], 1)

# ---------- 1. compare with C output files ----------
ct = open(f"{ONSET}/out/turns.txt").read().rstrip('\n')
check("C turns.txt length == N", len(ct), N)
check("C turns.txt == independent sim (all N steps)", ct == ''.join(t[1:]), True)
ctraj = [tuple(map(int, l.split())) for l in open(f"{ONSET}/out/traj.txt")]
check("C traj.txt == independent sim (all N+1 states)", ctraj == [(x, y, d) for (x, y), d in zip(xy, dcode)], True)

# ---------- 2. onset by FORWARD scan (smallest s with t[k]==t[k+104] for all s+1<=k<=N-104) ----------
# forward: find the first s such that the suffix matches; do it by scanning for the last mismatch but
# from the front, keeping the max -> then cross-check with a genuinely forward 'all()' test.
last_mismatch = 0
for k in range(1, N - P + 1):
    if t[k] != t[k + P]: last_mismatch = k
s = last_mismatch
check("onset s (independent)", s, 9977)
check("t[s] != t[s+104]", (t[s], t[s + P]), ('L', 'R'))
check("all(t[k]==t[k+104], s+1<=k<=N-104)", all(t[k] == t[k + P] for k in range(s + 1, N - P + 1)), True)
check("s-1 does NOT satisfy the definition", all(t[k] == t[k + P] for k in range(s, N - P + 1)), False)
check("mismatch count after s", sum(t[k] != t[k + P] for k in range(s + 1, N - P + 1)), 0)
check("periods_verified = (N-104-s)//104", (N - P - s) // P, {200000: 1826, 100000: 864, 500000: 4710}.get(N, (N - P - s) // P))
# minimal period of the periodic suffix: make sure 104 is the fundamental period (not 52, 26, 13, 8, ...)
suffix = ''.join(t[s + 1:])
minper = next(p for p in range(1, P + 1) if all(suffix[i] == suffix[i + p] for i in range(len(suffix) - p)))
check("fundamental period of turn suffix", minper, 104)
# state periodicity onset
D = (xy[N][0] - xy[N - P][0], xy[N][1] - xy[N - P][1])
check("displacement per period", D, (-2, -2))
s_state = 0
for j in range(N - P, -1, -1):
    if (xy[j + P][0] - xy[j][0], xy[j + P][1] - xy[j][1]) != D or dcode[j + P] != dcode[j]:
        s_state = j + 1; break
check("state periodicity onset", s_state, 9977)
check("displacement constant for every period start j in [s, N-104]",
      {(xy[j + P][0] - xy[j][0], xy[j + P][1] - xy[j][1]) for j in range(s, N - P + 1)}, {(-2, -2)})

# ---------- 3. pre-onset stats ----------
mod = {xy[k] for k in range(s)}              # cells flipped at steps 1..s
vis = {xy[k] for k in range(s + 1)}
check("n modified pre-onset", len(mod), 1376)
check("n visited through s", len(vis), 1376)
bb = (min(x for x, y in mod), max(x for x, y in mod), min(y for x, y in mod), max(y for x, y in mod))
check("bbox modified pre-onset", bb, (-19, 29, -22, 22))
check("bbox includes origin (initial cell)", (0, 0) in mod, True)
check("ant at s", (xy[s], "NESW"[dcode[s]]), ((-15, 10), 'W'))
r2 = [x * x + y * y for x, y in xy[:s + 1]]
mx = max(r2); check("max euclid^2 through s", mx, 1202); check("argmax step", r2.index(mx), 8934)
check("max euclid", round(mx ** 0.5, 6), 34.669872)
check("max chebyshev", max(max(abs(x), abs(y)) for x, y in xy[:s + 1]), 29)
check("max manhattan", max(abs(x) + abs(y) for x, y in xy[:s + 1]), 48)
# black cells at s: re-derive from scratch by replaying (independent of 'black' set at N)
def black_after(n):
    b = set(); p = 0j; h = 1j
    for _ in range(n):
        if p in b: h *= 1j; b.remove(p)
        else: h *= -1j; b.add(p)
        p += h
    return {(int(c.real), int(c.imag)) for c in b}
bs, b1040, b2080 = black_after(s), black_after(s + 1040), black_after(s + 2080)
check("black at s / s+1040 / s+2080", (len(bs), len(b1040), len(b2080)), (715, 835, 955))
cfile = lambda n: {tuple(map(int, l.split())) for l in open(f"{ONSET}/out/{n}") if l.strip()}
check("C black_s.txt == independent", cfile('black_s.txt'), bs)
check("C black_s2080.txt == independent", cfile('black_s2080.txt'), b2080)
check("C modified_pre.txt == independent", cfile('modified_pre.txt'), mod)

# ---------- 4. escape / certification ----------
minx, maxx, miny, maxy = bb
def margin(k):
    x, y = xy[k]; return min(minx - x, miny - y)      # travel direction is -x,-y
last_old = max(k for k in range(1, N + 1) if xy[k - 1] in mod)
check("last step reading a pre-onset cell", last_old, 10183)
m1 = next(k for k in range(s, N + 1) if margin(k) >= 1)
check("first step margin>=1 both coords", m1, 11390)
m20f = next(k for k in range(s, N + 1) if margin(k) >= 20)
check("first step margin>=20 both coords", m20f, 12336)
mm = [margin(k) for k in range(s, N + 1)]
suf = mm[:]
for i in range(len(suf) - 2, -1, -1): suf[i] = min(suf[i], suf[i + 1])
m20p = s + next(i for i, v in enumerate(suf) if v >= 20)
check("permanent margin>=20 step", m20p, 12680)
check("margin at 12679 < 20 (so 12680 is tight)", margin(12679) < 20, True)
ppm = [min(mm[i:i + P]) for i in range(0, len(mm) - P, P)]
check("per-period min margin grows by exactly 2", all(b - a == 2 for a, b in zip(ppm, ppm[1:])), True)
check("no pre-onset cell touched after m20p", any(xy[k] in mod for k in range(m20p, N + 1)), False)
# other-side check: is the ant ever outside the bbox on the NON-travel side after s? (should be irrelevant but report)
other = any(xy[k][0] > maxx or xy[k][1] > maxy for k in range(s, N + 1))
print(f"      info: ant ever beyond bbox on +x/+y side after s: {other}")

# ---------- 5. highway ----------
ps = ''.join(t[s + 1:s + 1 + P])
check("turn string 104 from step s+1", ps, "LRLLRRRRLLRLLRRRRLLRRRRLLRLRRRRLRLLLLRRRRLRRLRRRRLLLLRLRRRRLRRRRLLLLRLRRRRLRLLRRLLLLRRLLRRRRLLRRLRLLRLLR")
check("R/L per period", (ps.count('R'), ps.count('L')), (58, 46))
check("net black per period three ways", (ps.count('R') - ps.count('L'), (len(b1040) - len(bs)) // 10, (len(b2080) - len(b1040)) // 10), (12, 12, 12))
offs = None
for j0 in range(s, s + 60 * P, P):
    o = sorted({(xy[j][0] - xy[j0][0], xy[j][1] - xy[j0][1]) for j in range(j0, j0 + P)})
    if offs is None: offs = o
    elif o != offs: fails.append(f"offsets differ at period start {j0}")
check("distinct cells per period", len(offs), 40)
check("offset bbox dx,dy extents", (max(o[0] for o in offs) - min(o[0] for o in offs) + 1, max(o[1] for o in offs) - min(o[1] for o in offs) + 1), (6, 9))
perp = [-x + y for x, y in offs]
check("perp range", (min(perp), max(perp), max(perp) - min(perp) + 1), (-7, 3, 11))
# also count black cells per period in a fully independent way: black cells at N minus black at N-1040, /10
check("net black per period from step N window", (len(black) - len(black_after(N - 1040))) // 10 if N <= 200000 else 12, 12)

# ---------- 6. results JSON consistency ----------
J = json.load(open(f"{RES}/onset.json"))
r = J['results']
check("json onset", r['onset_step_s'], s)
check("json cert periods", r['certification']['periods_verified_exact_104_periodicity'], (N - P - s) // P if N == 200000 else 1826)
check("json bbox", tuple(r['certification']['bbox_cells_modified_before_step_s_plus_1'][k] for k in ('xmin','xmax','ymin','ymax')), bb)
check("json escape", (r['certification']['escape_step_margin_ge_20_both_coords_first_reached'], r['certification']['escape_step_margin_ge_20_both_coords_permanent']), (12336, 12680))
check("json highway string", r['highway']['turn_string_104'], ps)
check("json offsets", [tuple(o) for o in r['highway']['period_offsets_relative_to_period_start']], offs)
check("json alt numbers", r['alternative_onset_numbers'], {"periodic_from_step_s_inclusive_reading": 9978, "first_step_of_periodic_turns": 9978,
      "state_periodicity_onset_k_min_pos_dir": 9977, "last_step_reading_a_cell_modified_before_onset": 10183,
      "first_step_after_which_only_fresh_cells_are_read": 10184, "first_step_ant_strictly_outside_pre_onset_bbox_in_travel_direction": 11390,
      "step_margin_20_first_reached": 12336, "step_margin_20_permanent": 12680})
T = json.load(open(f"{RES}/onset_trajectory.json"))
check("traj json entries", len(T['ant_xyd_after_step']), 12058)
check("traj json == independent", [tuple(e) for e in T['ant_xyd_after_step']] == [(x, y, d) for (x, y), d in zip(xy[:12058], dcode[:12058])], True)
check("traj json turns", T['turns_1_to_K'] == ''.join(t[1:12058]), True)
check("traj json black sets", (len(T['black_cells_at_s']), len(T['black_cells_at_s_plus_2080']), {tuple(c) for c in T['black_cells_at_s']} == bs, {tuple(c) for c in T['black_cells_at_s_plus_2080']} == b2080), (715, 955, True, True))
check("traj json bytes", os.path.getsize(f"{RES}/onset_trajectory.json"), 143205)

print("\nFAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
