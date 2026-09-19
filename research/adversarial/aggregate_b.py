#!/usr/bin/env python3
"""Aggregate all Attack-B runs (out/attack_b_*.csv), re-verify the best configuration
with a fresh ./antsim run AND the pure-Python verify_py.py, and write
research/results/adversarial_best.json.  Usage: python3 aggregate_b.py"""
import csv, glob, json, os, subprocess, statistics
here = os.path.dirname(os.path.abspath(__file__)); res_dir = os.path.join(here, '..', 'results')
K = 12; LO = -(K // 2); NCELL = K * K
def cells_of_hex(h):
    bits = bin(int(h, 16))[2:].zfill(NCELL); return [[LO + i % K, LO + i // K] for i in range(NCELL) if bits[i] == '1']
runs = {}
for fn in sorted(glob.glob(os.path.join(here, 'out', 'attack_b_*.csv'))):
    name = os.path.basename(fn)[len('attack_b_'):-4]
    if not os.path.exists(fn[:-4] + '_summary.json'): print('skipping unfinished run', name); continue
    rows = list(csv.DictReader(open(fn)))
    on = [int(r['onset']) for r in rows]; on_s = sorted(on)
    q = lambda p: on_s[min(len(on_s) - 1, int(p * len(on_s)))]
    bi = max(range(len(rows)), key=lambda i: on[i])
    summ = json.load(open(fn[:-4] + '_summary.json'))
    runs[name] = dict(csv=os.path.relpath(fn, here), n_evals=len(rows), n_non_certified=sum(r['outcome'] != 'certified' for r in rows),
                      onset_max=on[bi], onset_mean=statistics.mean(on), onset_median=statistics.median(on),
                      p90=q(0.9), p99=q(0.99), p999=q(0.999), n_above_9977=sum(v > 9977 for v in on), n_above_100k=sum(v > 100000 for v in on),
                      n_above_200k=sum(v > 200000 for v in on), best_eval=int(rows[bi]['eval']), best_restart=int(rows[bi]['restart']),
                      best_genome_hex=rows[bi]['genome_hex'], best_cells=cells_of_hex(rows[bi]['genome_hex']),
                      restarts=summ['restarts'], lam=summ['lam'], stall=summ['stall'], start_k5=summ['start_k5'], seed=summ['seed'],
                      elapsed_s=summ['elapsed_s'], time_limit_s=summ.get('time_limit_s'))
best_name = max(runs, key=lambda n: runs[n]['onset_max']); b = runs[best_name]
cfg = os.path.join(here, 'out', 'attack_b_best.cfg')
open(cfg, 'w').write('# best Attack-B configuration (%s)\n' % best_name + ''.join(f'{x} {y}\n' for x, y in b['best_cells']))
r = json.loads(subprocess.run([os.path.join(here, 'antsim'), 'run', cfg, '--cap', '50000000', '--grid', '8192'], capture_output=True, text=True).stdout)
assert r['onset_step'] == b['onset_max'] and r['outcome'] == 'certified', r
py = subprocess.run(['python3', os.path.join(here, 'verify_py.py'), cfg, str(b['onset_max'] + 104 * 40)], capture_output=True, text=True)
pyr = json.loads(py.stdout.split('\n')[0]); assert pyr['python_onset'] == b['onset_max'] and py.returncode == 0, py.stdout
# also: the best from the main (20,000-eval) run only
main = {n: v for n, v in runs.items() if n.startswith('main')}
main_best = max(main, key=lambda n: main[n]['onset_max']) if main else None
out = dict(experiment='adversarial_best', conventions='CONVENTIONS.md',
           description='Longest certified highway onset found by the Attack-B evolutionary search over initial configurations in the 12x12 box (x,y in -6..5), ant at (0,0) facing North.',
           box=dict(k=12, xmin=-6, xmax=5, ymin=-6, ymax=5),
           black_cells=b['best_cells'], n_black=len(b['best_cells']), onset_step=b['onset_max'], ratio_to_empty_grid=b['onset_max'] / 9977,
           direction=r['direction'], displacement_per_period=r['disp'], period=104, certification_step=r['cert_step'],
           periods_verified_at_certification=r['periods_verified'], bbox_pre_onset=r['bbox_pre_onset'], final_pos=r['final_pos'],
           found_in_run=best_name, found_at_eval=b['best_eval'], genome_hex=b['best_genome_hex'],
           python_cross_check=dict(script='verify_py.py', steps=b['onset_max'] + 104 * 40, python_onset=pyr['python_onset'], python_direction=pyr['python_direction'], agree=True),
           main_run_20000_evals_best=dict(run=main_best, onset_step=main[main_best]['onset_max'], cells=main[main_best]['best_cells']) if main_best else None,
           any_evaluation_hit_cap=any(v['n_non_certified'] > 0 for v in runs.values()),
           reproduce=f'cd research/adversarial && ./antsim run out/attack_b_best.cfg   (and python3 verify_py.py out/attack_b_best.cfg {b["onset_max"] + 104 * 40})',
           runs=runs)
json.dump(out, open(os.path.join(res_dir, 'adversarial_best.json'), 'w'), indent=1)
json.dump(runs, open(os.path.join(here, 'out', 'attack_b_runs.json'), 'w'), indent=1)
for n, v in runs.items(): print(n, 'evals', v['n_evals'], 'max', v['onset_max'], 'mean %.0f' % v['onset_mean'], 'p99', v['p99'], '>100k', v['n_above_100k'], 'noncert', v['n_non_certified'])
print('BEST', best_name, b['onset_max'], r['direction'], 'python agrees:', pyr['python_onset'])
