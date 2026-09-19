#!/usr/bin/env python3
"""Characterize the highway and write results JSON files from the C simulator output.
Usage: python3 analyze.py OUTDIR RESULTS_DIR
Writes RESULTS_DIR/onset.json and RESULTS_DIR/onset_trajectory.json
"""
import sys, json, math
out, resdir = sys.argv[1], sys.argv[2]

kv = {}
for line in open(f"{out}/onset.txt"):
    k, v = line.rstrip('\n').split('=', 1)
    kv[k] = v
N = int(kv['N']); P = int(kv['period']); s = int(kv['s'])
turns = '?' + open(f"{out}/turns.txt").read().strip()   # turns[k] = t[k], k=1..N
assert len(turns) == N + 1
traj = []
with open(f"{out}/traj.txt") as f:
    for line in f:
        x, y, d = map(int, line.split()); traj.append((x, y, d))
assert len(traj) == N + 1

def load_cells(name):
    return [list(map(int, l.split())) for l in open(f"{out}/{name}") if l.strip()]

# ---- 1. onset: recompute from the turn string (independent of C's computation) ----
s_py = 0
for k in range(N - P, 0, -1):
    if turns[k] != turns[k + P]:
        s_py = k; break
assert s_py == s, (s_py, s)
assert turns[s] != turns[s + P]
assert all(turns[k] == turns[k + P] for k in range(s + 1, N - P + 1))
# alternative readings
s_alt_from_s = s + 1        # "periodic from step s onward" reading would report s+1
# state periodicity: smallest k with (pos[j+104]-pos[j], dir) constant for all j>=k
D = (traj[N][0] - traj[N - P][0], traj[N][1] - traj[N - P][1])
s_state = 0
for j in range(N - P, -1, -1):
    a, b = traj[j], traj[j + P]
    if (b[0] - a[0], b[1] - a[1]) != D or a[2] != b[2]:
        s_state = j + 1; break

# ---- 2. certification ----
periods_checked = (N - P - s) // P            # complete periods with k and k+104 both inside [s+1, N]
assert periods_checked >= 20
ax, ay, ad = traj[s]
minx, maxx, miny, maxy = map(int, kv['bbox_modified_pre_onset'].split())
# recompute the bbox from the trajectory: cells modified at steps 1..s are positions after steps 0..s-1
mod = set((traj[k][0], traj[k][1]) for k in range(s))
assert (min(x for x, y in mod), max(x for x, y in mod), min(y for x, y in mod), max(y for x, y in mod)) == (minx, maxx, miny, maxy)
assert len(mod) == int(kv['n_modified_pre_onset'])
sx = -1 if D[0] < 0 else 1; sy = -1 if D[1] < 0 else 1
def margin(k):
    x, y, _ = traj[k]
    mx = (minx - x) if sx < 0 else (x - maxx)
    my = (miny - y) if sy < 0 else (y - maxy)
    return mx, my
m20_first = next(k for k in range(s, N + 1) if min(margin(k)) >= 20)
m1 = next(k for k in range(s, N + 1) if min(margin(k)) >= 1)
assert m20_first == int(kv['escape_step_margin20'])
# the ant wobbles within a period, so use the suffix minimum: m20 = smallest k such that
# margin(j) >= 20 for ALL j >= k (within the simulated range). Also check the per-period
# minimum margin is non-decreasing (it grows by 2 per period), which is what makes it permanent.
mm = [min(margin(k)) for k in range(s, N + 1)]
suf = mm[:]
for i in range(len(suf) - 2, -1, -1):
    suf[i] = min(suf[i], suf[i + 1])
m20 = s + next(i for i in range(len(suf)) if suf[i] >= 20)
assert all(min(margin(k)) >= 20 for k in range(m20, N + 1))
per_period_min = [min(mm[i:i + P]) for i in range(0, len(mm) - P, P)]
assert all(b >= a for a, b in zip(per_period_min, per_period_min[1:]))
assert all(b - a == 2 for a, b in zip(per_period_min, per_period_min[1:]))   # exact +2 per period from step s on
# after m20, the ant never touches a modified-pre cell (consistency)
assert all((traj[k][0], traj[k][1]) not in mod for k in range(m20, N + 1))
# last step reading a chaos-era cell
last_old = max(k for k in range(1, N + 1) if (traj[k - 1][0], traj[k - 1][1]) in mod)
assert last_old == int(kv['last_step_reading_chaos_cell'])

# ---- 3. highway characterization ----
period_string = turns[s + 1: s + 1 + P]
nR = period_string.count('R'); nL = period_string.count('L')
# per-period displacement, checked for every period start j in [s, N-104]
disp = set((traj[j + P][0] - traj[j][0], traj[j + P][1] - traj[j][1]) for j in range(s, N - P + 1))
assert disp == {D}
dirs = set(traj[j][2] for j in range(s, N - P + 1, P))
# offsets touched within one period, relative to position at period start (use j = s + 20*104, deep in highway)
j0 = s + 20 * P
offs = sorted(set((traj[j][0] - traj[j0][0], traj[j][1] - traj[j0][1]) for j in range(j0, j0 + P)))
# same set for every period start? check translation invariance for a few periods
for jj in range(s, s + 40 * P, P):
    o = sorted(set((traj[j][0] - traj[jj][0], traj[j][1] - traj[jj][1]) for j in range(jj, jj + P)))
    assert o == offs, jj
# strip coordinates: travel direction u = D/|D| ~ (sx, sy)/sqrt2; perpendicular v = (sx, -sy)/sqrt2
# perp coordinate (in units of cells along a diagonal lattice line) = sx*x - sy*y ; along = sx*x + sy*y
perp = [sx * x - sy * y for x, y in offs]; along = [sx * x + sy * y for x, y in offs]
# black cells per period in the trail: difference of black counts between s+1040 and s+2080 (10 periods)
b_s, b_1040, b_2080 = int(kv['black_at_s']), int(kv['black_at_s1040']), int(kv['black_at_s2080'])
assert (b_2080 - b_1040) % 10 == 0 and (b_1040 - b_s) % 10 == 0
black_per_period = (b_2080 - b_1040) // 10
assert black_per_period == (b_1040 - b_s) // 10 == nR - nL
# trail geometry. s+2080 = s + 20*104 is a period start. Take the black cells at step s+2080 in a window of
# exactly 10 periods well behind the ant (along-coordinate a = sx*(x-xa)+sy*(y-ya) in [-60,-20); a grows by 4
# per period) and ahead of the chaos region. Canonicalize each cell by shifting it by k*(D) so that a lies in
# [-24,-20): the result must be exactly 12 distinct offsets (= black cells per period), each seen 10 times.
black_2080 = load_cells('black_s2080.txt')
black_s = load_cells('black_s.txt')
xa, ya, _ = traj[s + 2080]
assert (s + 2080 - s) % P == 0
win = []
for x, y in black_2080:
    a = sx * (x - xa) + sy * (y - ya)
    if -60 <= a < -20:
        win.append((x, y))
assert len(win) == 10 * black_per_period, len(win)
canon = {}
for x, y in win:
    a = sx * (x - xa) + sy * (y - ya)
    k = (a + 24) // 4          # shift by k periods forward so that a - 4k in [-24,-20)
    cx, cy = x - xa - k * D[0], y - ya - k * D[1]
    canon[(cx, cy)] = canon.get((cx, cy), 0) + 1
assert len(canon) == black_per_period and set(canon.values()) == {10}, canon
trail_offsets = sorted(canon)
trail_perp = sorted(set(sx * x - sy * y for x, y in trail_offsets))
# also verify: every cell in the window was touched by the ant (it is on the strip) -- sanity
strip_cells = set((traj[j][0], traj[j][1]) for j in range(s, s + 2081))
assert all(c in strip_cells for c in win)
# ant distance statistics
maxd = float(kv['max_euclid_dist_through_s'])

res = {
  "experiment": "onset",
  "conventions": "CONVENTIONS.md",
  "parameters": {"initial_configuration": "empty grid", "steps_simulated": N, "period_tested": P,
                 "grid": "dynamic byte grid, side 2*(2N/104)+512, origin centered, bounds guarded every step",
                 "simulator": "research/onset/ant.c (gcc -O2)", "cross_check": "research/onset/verify_py.py (pure Python, first 15000 steps)"},
  "results": {
    "onset_step_s": s,
    "onset_definition": "smallest s>=0 with t[k]==t[k+104] for all k>=s+1 (k+104<=N); t[s]!=t[s+104]",
    "t_at_s": turns[s], "t_at_s_plus_104": turns[s + P],
    "alternative_onset_numbers": {
      "periodic_from_step_s_inclusive_reading": s_alt_from_s,
      "first_step_of_periodic_turns": s + 1,
      "state_periodicity_onset_k_min_pos_dir": s_state,
      "last_step_reading_a_cell_modified_before_onset": last_old,
      "first_step_after_which_only_fresh_cells_are_read": last_old + 1,
      "first_step_ant_strictly_outside_pre_onset_bbox_in_travel_direction": m1,
      "step_margin_20_first_reached": m20_first,
      "step_margin_20_permanent": m20
    },
    "certification": {
      "periods_verified_exact_104_periodicity": periods_checked,
      "turn_mismatches_after_s_in_simulated_range": 0,
      "bbox_cells_modified_before_step_s_plus_1": {"xmin": minx, "xmax": maxx, "ymin": miny, "ymax": maxy,
                                                    "width": maxx - minx + 1, "height": maxy - miny + 1},
      "ant_at_step_s": {"x": ax, "y": ay, "dir": "NESW"[ad]},
      "highway_direction": ("+x" if sx > 0 else "-x") + "," + ("+y" if sy > 0 else "-y"),
      "escape_step_margin_ge_20_both_coords_first_reached": m20_first,
      "escape_step_margin_ge_20_both_coords_permanent": m20,
      "margin_at_escape_step": {"x": margin(m20)[0], "y": margin(m20)[1]},
      "per_period_min_margin_grows_by_2_each_period": True,
      "margin_never_below_20_after_escape_step_within_N": True,
      "ant_never_touches_pre_onset_cell_after_escape_step_within_N": True,
      "argument": "From step m20 on, every later position lies on the 104-periodic strip (offsets 'period_offsets' translated by multiples of the displacement (-2,-2)), whose perpendicular extent is bounded; the strip moves away from the bbox monotonically so no previously modified cell is ever read again, hence the periodic turn sequence continues forever."
    },
    "highway": {
      "period": P,
      "displacement_per_period": {"dx": D[0], "dy": D[1]},
      "direction_at_period_starts": sorted("NESW"[d] for d in dirs),
      "turns_per_period": {"R": nR, "L": nL},
      "turn_string_104": period_string,
      "turn_string_start_step": s + 1,
      "period_offsets_relative_to_period_start": [list(o) for o in offs],
      "n_distinct_cells_touched_per_period": len(offs),
      "perp_coordinate_range": {"min": min(perp), "max": max(perp), "n_diagonal_lines": max(perp) - min(perp) + 1,
                                "definition": "perp = sx*dx - sy*dy with (sx,sy)=sign(displacement); each integer value is one lattice diagonal line x-y=const (spacing 1/sqrt(2) cell); the strip occupies n_diagonal_lines consecutive lines, geometric width (n-1)/sqrt(2) = 7.07 cell widths"},
      "along_coordinate_range": {"min": min(along), "max": max(along)},
      "strip_width_cells_perpendicular_bbox": {"dx_extent": max(o[0] for o in offs) - min(o[0] for o in offs) + 1,
                                               "dy_extent": max(o[1] for o in offs) - min(o[1] for o in offs) + 1},
      "black_cells_added_per_period": black_per_period,
      "black_count_at_s": b_s, "black_count_at_s_plus_1040": b_1040, "black_count_at_s_plus_2080": b_2080,
      "trail_black_offsets_per_period_relative_to_ant_at_period_start": [list(o) for o in trail_offsets],
      "trail_black_offsets_note": "offsets (dx,dy) from the ant position at a period start, for the 12 black cells left per period in the settled trail (canonicalized into the along-window [-24,-20)); the full trail is this set translated by multiples of (-2,-2)",
      "trail_perp_lines_occupied": trail_perp
    },
    "pre_onset": {
      "distinct_cells_visited_steps_0_to_s": int(kv['n_visited_through_s']),
      "distinct_cells_modified_steps_1_to_s": int(kv['n_modified_pre_onset']),
      "black_cells_at_onset": b_s,
      "bbox_at_onset": {"xmin": minx, "xmax": maxx, "ymin": miny, "ymax": maxy, "width": maxx - minx + 1, "height": maxy - miny + 1},
      "max_euclid_distance_from_origin_steps_0_to_s": maxd,
      "max_euclid_distance_step": int(kv['argmax_step']),
      "max_chebyshev_distance": int(kv['max_cheb_through_s']),
      "max_manhattan_distance": int(kv['max_manhattan_through_s'])
    }
  },
  "notes": [
    "Coordinates: x East, y North; directions N=(0,+1),E,S,W; step count = number of rule applications.",
    "traj[k] = ant (x,y,dir) after k steps; the cell read at step k is traj[k-1].",
    "Cells 'modified before step s+1' = positions after steps 0..s-1 (each step flips the cell the ant stands on).",
    "Reproduce: cd research/onset && make all (see README.md)."
  ]
}
json.dump(res, open(f"{resdir}/onset.json", "w"), indent=1)

# ---- 5. trajectory export for the movie ----
K = s + 2080
tj = {
  "experiment": "onset", "conventions": "CONVENTIONS.md",
  "onset_step_s": s, "period": P, "displacement_per_period": list(D),
  "steps_included": [0, K],
  "ant_xyd_after_step": [[x, y, d] for x, y, d in traj[:K + 1]],
  "dir_encoding": "0=N,1=E,2=S,3=W",
  "turns_1_to_K": turns[1:K + 1],
  "black_cells_at_s": black_s,
  "black_cells_at_s_plus_2080": black_2080,
  "bbox_modified_pre_onset": [minx, maxx, miny, maxy]
}
json.dump(tj, open(f"{resdir}/onset_trajectory.json", "w"), separators=(',', ':'))
print(json.dumps(res["results"], indent=1))
