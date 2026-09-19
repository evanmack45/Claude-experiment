#!/usr/bin/env python3
"""Attack A: obstacle on the road.
1. Pure-Python simulation of the EMPTY grid to locate the certified highway (period
   positions after the escape step 12680, displacement (-2,-2) per 104 steps).
2. For each shape x distance x lateral offset x phase, place the obstacle as a NEW
   initial configuration on the otherwise empty grid and simulate from scratch with
   ./antsim batch (cap 50,000,000).
Writes out/attack_a.jsonl (one result per placement, with the placement metadata)
and out/attack_a_summary.json.
Usage: python3 attack_a.py
"""
import json, subprocess, os, sys, statistics
here = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(here, 'out'), exist_ok=True)

# ---- 1. locate the highway of the empty grid (pure Python, independent of antsim) ----
DX = [0, 1, 0, -1]; DY = [1, 0, -1, 0]
black = set(); x = y = d = 0; pos = [(0, 0)]; t = []
N = 13500
for k in range(1, N + 1):
    if (x, y) in black: d = (d + 3) % 4; black.discard((x, y)); t.append('L')
    else: d = (d + 1) % 4; black.add((x, y)); t.append('R')
    x += DX[d]; y += DY[d]; pos.append((x, y))
s = max(k for k in range(1, N - 104 + 1) if t[k-1] != t[k+103])
assert s == 9977, s
ESC = 12680                      # margin >= 20 permanent from here (research/results/onset.json)
P0 = pos[ESC]                    # position after step ESC = start of a period
period_cells = sorted(set(pos[ESC + i] for i in range(0, 104)))   # positions after steps ESC..ESC+103
disp = (pos[ESC + 104][0] - P0[0], pos[ESC + 104][1] - P0[1])
assert disp == (-2, -2), disp
# strip geometry: along-axis u = -(x+y) increases with travel; perpendicular v = x - y
vs = [px - py for px, py in period_cells]
strip_v = (min(vs), max(vs))
pre_onset_bbox = [min(p[0] for p in pos[:s+1]), min(p[1] for p in pos[:s+1]), max(p[0] for p in pos[:s+1]), max(p[1] for p in pos[:s+1])]

SHAPES = {
    '1x1':   [(0, 0)],
    '2x2':   [(0, 0), (1, 0), (0, 1), (1, 1)],
    '3x3':   [(i, j) for i in range(3) for j in range(3)],
    'hline5': [(i, 0) for i in range(5)],
    'vline5': [(0, i) for i in range(5)],
    'L3':    [(0, 0), (1, 0), (2, 0), (0, 1), (0, 2)],
}
DISTANCES = [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]   # periods ahead of P0
LATERAL = list(range(-8, 9, 2))                                      # offset along (1,-1)
PHASES = [0, 1]                                                       # extra shift along (-1,-1)

placements = []
for shape, cells in SHAPES.items():
    for m in DISTANCES:
        for dv in LATERAL:
            for ph in PHASES:
                ax = P0[0] + m * disp[0] + dv - ph
                ay = P0[1] + m * disp[1] - dv - ph
                obst = [(ax + cx, ay + cy) for cx, cy in cells]
                on_strip = any(strip_v[0] <= (cx - cy) <= strip_v[1] for cx, cy in obst)
                placements.append(dict(shape=shape, periods_ahead=m, lateral=dv, phase=ph, anchor=[ax, ay],
                                       cells=obst, obstacle_v_in_strip=on_strip))
print(f"highway located: s={s}, P0={P0}, disp={disp}, strip v-range={strip_v}, {len(placements)} placements", file=sys.stderr)

# ---- 2. simulate every placement from scratch ----
inp = '\n'.join(' '.join(f'{cx},{cy}' for cx, cy in p['cells']) for p in placements) + '\n'
proc = subprocess.run([os.path.join(here, 'antsim'), 'batch', '--cap', '50000000', '--grid', '8192'],
                      input=inp, capture_output=True, text=True)
lines = proc.stdout.strip().split('\n')
assert len(lines) == len(placements), (len(lines), proc.stderr[:500])
results = []
with open(os.path.join(here, 'out', 'attack_a.jsonl'), 'w') as f:
    for p, ln in zip(placements, lines):
        r = json.loads(ln); r.update(p)
        r['contact_step'] = r['first_initial_black_read']
        r['extra_chaos'] = (r['onset_step'] - r['contact_step']) if r['contact_step'] else None
        results.append(r); f.write(json.dumps(r) + '\n')

def stats(v):
    v = sorted(v)
    if not v: return {}
    q = lambda p: v[min(len(v)-1, int(p * len(v)))]
    return dict(n=len(v), min=v[0], max=v[-1], mean=statistics.mean(v), median=statistics.median(v),
                p10=q(0.10), p25=q(0.25), p75=q(0.75), p90=q(0.90), p99=q(0.99))

hit = [r for r in results if r['contact_step'] > 0]
miss = [r for r in results if r['contact_step'] == 0]
outcomes = {}
for r in results: outcomes[r['outcome']] = outcomes.get(r['outcome'], 0) + 1
dirs = {}
for r in hit: dirs[r['direction']] = dirs.get(r['direction'], 0) + 1
best = max(results, key=lambda r: r['onset_step'])
best_extra = max(hit, key=lambda r: r['extra_chaos'])
per_shape = {sh: dict(n_hit=len([r for r in hit if r['shape'] == sh]),
                      extra_chaos=stats([r['extra_chaos'] for r in hit if r['shape'] == sh]),
                      onset=stats([r['onset_step'] for r in hit if r['shape'] == sh])) for sh in SHAPES}
per_dist = {str(m): dict(n_hit=len([r for r in hit if r['periods_ahead'] == m]),
                         extra_chaos=stats([r['extra_chaos'] for r in hit if r['periods_ahead'] == m])) for m in DISTANCES}
summary = dict(
    empty_grid_onset=s, highway_period_start_after_escape=dict(step=ESC, pos=list(P0)), disp_per_period=list(disp),
    strip_perpendicular_range_v_eq_x_minus_y=list(strip_v), period_cells=[list(c) for c in period_cells],
    pre_onset_bbox=pre_onset_bbox,
    n_placements=len(results), shapes=list(SHAPES), distances_periods=DISTANCES, lateral_offsets=LATERAL, phases=PHASES,
    outcome_counts=outcomes, n_obstacle_hit=len(hit), n_obstacle_missed=len(miss),
    all_missed_have_onset_9977=all(r['onset_step'] == 9977 for r in miss),
    missed_onsets=sorted(set(r['onset_step'] for r in miss)),
    all_hit_reformed_highway=all(r['outcome'] == 'certified' for r in hit),
    direction_counts_after_hit=dirs,
    onset_hit=stats([r['onset_step'] for r in hit]),
    extra_chaos_hit=stats([r['extra_chaos'] for r in hit]),
    contact_step_hit=stats([r['contact_step'] for r in hit]),
    frac_hit_with_extra_chaos_below_9977=sum(r['extra_chaos'] < 9977 for r in hit) / max(1, len(hit)),
    per_shape=per_shape, per_distance=per_dist,
    longest_onset=best, longest_extra_chaos=best_extra,
    max_steps_simulated=max(r['steps_simulated'] for r in results),
)
json.dump(summary, open(os.path.join(here, 'out', 'attack_a_summary.json'), 'w'), indent=1)
print(json.dumps({k: v for k, v in summary.items() if k not in ('period_cells', 'per_shape', 'per_distance', 'longest_onset', 'longest_extra_chaos')}, indent=1))
print("longest onset:", best['onset_step'], best['shape'], best['periods_ahead'], best['lateral'], best['phase'], best['cells'])
print("longest extra chaos:", best_extra['extra_chaos'], best_extra['shape'], best_extra['periods_ahead'], best_extra['lateral'], best_extra['phase'])
