#!/usr/bin/env python3
"""Assemble research/results/adversarial.json from the outputs of attacks A-D.
Usage: python3 make_results.py"""
import json, os, subprocess
here = os.path.dirname(os.path.abspath(__file__)); res = os.path.join(here, '..', 'results')
L = lambda p: json.load(open(os.path.join(here, 'out', p)))
A = L('attack_a_summary.json'); C = L('attack_c_summary.json'); Bruns = L('attack_b_runs.json'); Bbest = json.load(open(os.path.join(res, 'adversarial_best.json')))
D = L('attack_d_summary.json') if os.path.exists(os.path.join(here, 'out', 'attack_d_summary.json')) else None
EMPTY = 9977
def strip(r, keys): return {k: v for k, v in r.items() if k not in keys}
# cap-path sanity tests (the cap/nontravel/boundary branches of the tool, exercised on the empty grid)
sanity = {}
for name, args in {'cap_5000': ['--cap', '5000'], 'nontravel_cap_12200': ['--cap', '12200'], 'boundary_grid_32': ['--cap', '5000', '--grid', '32']}.items():
    sanity[name] = json.loads(subprocess.run([os.path.join(here, 'antsim'), 'run', os.path.join(here, 'out', 'empty.cfg')] + args, capture_output=True, text=True).stdout)
# every non-certified run anywhere?
noncert = []
noncert += [r for r in map(json.loads, open(os.path.join(here, 'out', 'attack_a.jsonl'))) if r['outcome'] != 'certified']
noncert += [r for r in map(json.loads, open(os.path.join(here, 'out', 'attack_c.jsonl'))) if r['outcome'] != 'certified']
noncert += [dict(run=n, n=v['n_non_certified']) for n, v in Bruns.items() if v['n_non_certified'] > 0]
if D: noncert += [dict(attack='D', stage=s['stage'], n=s['n_candidates_noncertified']) for s in D['stages'] if s.get('n_candidates_noncertified', 0) > 0]
candidates = [('A', A['longest_onset']['onset_step'], A['longest_onset']['cells']), ('B', Bbest['onset_step'], Bbest['black_cells']), ('C', C['longest']['onset_step'], C['longest']['cells'])]
if D: candidates.append(('D', D['final_onset'], D['cells']))
overall = max(candidates, key=lambda c: c[1])
total_evals = A['n_placements'] + C['n_configs'] + sum(v['n_evals'] for v in Bruns.values()) + (sum(s.get('n_candidates', 0) + 1 for s in D['stages']) + 1 if D else 0)
out = dict(
  experiment='adversarial', conventions='CONVENTIONS.md',
  description='Adversarial attacks on the Langton\'s-ant highway conjecture: obstacles on the empty-grid highway (A), evolutionary search for the longest onset in the 12x12 box (B), hand-designed structured seeds (C), and greedy obstacle chaining in a bounded box (D). Every run uses the certified highway detection of CONVENTIONS.md.',
  parameters=dict(
    simulator='research/adversarial/antsim.c (gcc -O3 -march=native); ./antsim run <cfg> | ./antsim batch',
    step_cap=50000000, grid='8192x8192 byte grid, origin at (4096,4096); reaching the outer ring is reported as outcome=boundary (never wrapped)',
    period=104, onset_step_definition='s = max{k>=1 : t[k] != t[k+104]} (0 if no mismatch); t[k]=R iff step k turned right (cell white); equivalently the smallest s with t[k]==t[k+104] for all k>=s+1',
    certification='at step n >= s+2184: t[k]==t[k+104] verified for all k in s+1..n-104 (>=20 full periods) AND ant >= 20 cells beyond the bbox of {origin, initial black cells, cells modified in steps 1..s} in both coordinates in the travel direction (sign of pos(n)-pos(n-104), both nonzero). Identical to research/exhaustive and research/random.',
    cross_checks='antsim reproduces onset.json (9977), exhaustive.json k=1..5 maxima (9978, 43264, 233232) and verify_py.py (independent pure Python) agrees on every configuration it was run on',
    empty_grid_onset=EMPTY,
    attack_A=dict(shapes=A['shapes'], distances_periods_ahead_of_escape_point=A['distances_periods'], lateral_offsets_along_1_minus1=A['lateral_offsets'], phases=A['phases'],
                  placement='anchor = P0 + m*(-2,-2) + dv*(1,-1) - ph*(1,1), P0 = ant position after step 12680 (first period start after the escape margin becomes permanent) = ' + str(A['highway_period_start_after_escape']['pos']) + '; obstacle placed with its lower-left cell at the anchor on an otherwise EMPTY grid and simulated from scratch'),
    attack_B=dict(box='12x12, x,y in -6..5', algorithm='(1+lambda) hill-climb, mutation flips r cells with r uniform in {1,2,3}, child accepted if onset >= parent, restart from random density U(0.2,0.8) after `stall` evaluations without strict improvement; objective = onset (non-certified = 1e18)',
                  main_run=dict(total_evaluations=sum(v['n_evals'] for n, v in Bruns.items() if n.startswith('main')), processes=2, seeds=[v['seed'] for n, v in Bruns.items() if n.startswith('main')], lam=4, stall=600, note='seed 2 first restart starts from the k=5 exhaustive maximum (233232); seed 1 purely random'),
                  extended_run=dict(total_evaluations=sum(v['n_evals'] for n, v in Bruns.items() if n.startswith('ext')), processes=2, seeds=[v['seed'] for n, v in Bruns.items() if n.startswith('ext')], lam=8, stall=2000, wall_clock_limit_s=900, note='seed 12 first restart starts from the k=5 exhaustive maximum; seed 11 purely random')),
    attack_C=dict(n_configs=C['n_configs'], families=list(C['per_family'])),
    attack_D=dict(box_halfwidth=D['box_halfwidth'], obstacle='2x2 block', candidates_per_stage='phase i in 0,3,..,102 of one highway period, minimal distance m with the block untouched and inside the box; the candidate with the longest onset is kept') if D else None,
    cap_rerun_policy='any non-certified run is re-run with --cap 500000000 --grid 32768 --log-every 10000000 (script rerun_cap.sh); none was needed',
  ),
  results=dict(
    total_configurations_simulated=total_evals, total_non_certified=len(noncert), non_certified_runs=noncert,
    any_run_hit_cap=len(noncert) > 0,
    overall_longest_onset=dict(attack=overall[0], onset_step=overall[1], ratio_to_empty_grid=overall[1] / EMPTY, n_black=len(overall[2]), black_cells=overall[2]),
    longest_onset_bounded_12x12_box=dict(onset_step=Bbest['onset_step'], ratio_to_empty_grid=Bbest['ratio_to_empty_grid'], black_cells=Bbest['black_cells'], direction=Bbest['direction'], found_in_run=Bbest['found_in_run'], file='research/results/adversarial_best.json'),
    attack_A=strip(A, ('period_cells',)),
    attack_B=dict(runs=Bruns, best=strip(Bbest, ('runs',)), any_evaluation_hit_cap=Bbest['any_evaluation_hit_cap'],
                  main_20000_eval_best=Bbest['main_run_20000_evals_best'],
                  observation='the (1+lambda) climb barely beats random sampling: the onset landscape is chaotic (single-cell flips reshuffle the onset almost completely), the k=5 exhaustive maximum 233232 survived every mutation neighbourhood search around it'),
    attack_C=C,
    attack_D=strip(D, ('final',)) if D else None,
    tool_outcome_branch_sanity_tests=sanity,
  ),
  notes=[
    'Every configuration simulated (A: %d, B: %d, C: %d%s) reached a certified 104-periodic highway; no run hit the 50,000,000-step cap, so the 500,000,000-cap re-run policy (step 5) was never triggered.' % (A['n_placements'], sum(v['n_evals'] for v in Bruns.values()), C['n_configs'], (', D: %d' % (sum(s.get('n_candidates', 0) + 1 for s in D['stages']) + 1)) if D else ''),
    'Attack A: an obstacle on the highway always throws the ant back into chaos and a new highway always re-forms (616/616 hits, direction re-randomised: see direction_counts_after_hit); onset for a hit = contact step + extra chaos; extra chaos has median ~5k and max ~139k, i.e. the same distribution scale as onsets from random seeds; misses give exactly 9977.',
    'Onset for an obstacle placed m periods ahead is trivially >= 12680 + 104 m, so "longest onset" is unbounded in an unbounded box; the meaningful adversarial numbers are (i) extra chaos after contact and (ii) longest onset in a bounded box (attack B 12x12; attack D |x|,|y|<=%s).' % (D['box_halfwidth'] if D else '-'),
    'Ambiguity: CONVENTIONS.md defines s as the smallest s with t[k]==t[k+104] for all k>=s+1; the alternative reading "periodic from step s inclusive" would add 1 to every onset reported here.',
    'Non-certified outcome labels: cap (not periodic for 20 periods at the cap), nontravel (periodic but escape margin not yet reached at the cap), boundary (grid edge). All three branches were exercised deliberately on the empty grid with tiny caps/grids (tool_outcome_branch_sanity_tests).',
  ])
json.dump(out, open(os.path.join(res, 'adversarial.json'), 'w'), indent=1)
print('overall longest', overall[0], overall[1], 'ratio %.2f' % (overall[1] / EMPTY), '| noncert', len(noncert), '| total sims', total_evals)
