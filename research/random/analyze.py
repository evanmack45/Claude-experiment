#!/usr/bin/env python3
"""Aggregate the random-configuration sweeps and write
   research/results/random_samples.csv   (k,p,seed,sample_index,outcome,onset_step,direction,steps_simulated)
   research/results/random_longest.json  (the configuration with the longest certified onset)
   research/results/random.json          (per-cell aggregates, totals, scaling fits, extended sweeps)
Usage: python3 analyze.py   (run from anywhere; paths are absolute)
"""
import csv, json, os, glob, subprocess, statistics, sys
import numpy as np

D = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(D, '..', 'results')
KS = [5, 8, 12, 16, 24, 32, 48, 64]
PS = [0.1, 0.25, 0.5, 0.75, 0.9]
SEED_MAIN = 20260919
CAP = 20000000
COLS = ['k', 'p', 'seed', 'sample_index', 'outcome', 'onset_step', 'direction', 'steps_simulated',
        'n_black', 'dispx', 'dispy', 'fx', 'fy', 'bx0', 'by0', 'bx1', 'by1', 'periods_verified']

def load_main():
    rows = []
    for f in ('procA.csv', 'procB.csv'):
        with open(os.path.join(D, 'out', f)) as fh:
            for r in csv.reader(fh):
                assert len(r) == len(COLS), r
                d = dict(zip(COLS, r))
                for c in COLS:
                    if c in ('p',): d[c] = float(d[c])
                    elif c in ('outcome', 'direction'): pass
                    else: d[c] = int(d[c])
                rows.append(d)
    return rows

def pct(a, q):
    return float(np.percentile(a, q, method='lower'))

def stats_of(s):
    a = np.asarray(s, dtype=np.int64)
    if len(a) == 0: return None
    return {'min': int(a.min()), 'mean': float(a.mean()), 'median': float(np.median(a)),
            'max': int(a.max()), 'std': float(a.std()),
            'percentiles': {str(q): pct(a, q) for q in (1, 5, 10, 25, 75, 90, 95, 99, 99.9)},
            'frac_below_9977': float((a < 9977).mean()), 'frac_above_9977': float((a > 9977).mean())}

def fit_loglog(xs, ys):
    """least squares fit log(y) = a + b log(x); returns dict with exponent b, prefactor exp(a), r2."""
    lx, ly = np.log(np.asarray(xs, float)), np.log(np.asarray(ys, float))
    A = np.vstack([np.ones_like(lx), lx]).T
    coef, res, _, _ = np.linalg.lstsq(A, ly, rcond=None)
    pred = A @ coef
    ss_res = float(((ly - pred) ** 2).sum()); ss_tot = float(((ly - ly.mean()) ** 2).sum())
    return {'exponent': float(coef[1]), 'prefactor': float(np.exp(coef[0])), 'r2': 1 - ss_res / ss_tot if ss_tot > 0 else None,
            'x': [float(v) for v in xs], 'y': [float(v) for v in ys], 'n_points': len(xs)}

def main():
    rows = load_main()
    # ---- sanity: every cell has exactly 10000 distinct sample indices, one seed
    cells = {}
    for r in rows: cells.setdefault((r['k'], r['p']), []).append(r)
    assert sorted(cells) == sorted((k, p) for k in KS for p in PS), sorted(cells)
    for key, rs in cells.items():
        assert len(rs) == 10000 and len({r['sample_index'] for r in rs}) == 10000 and {r['seed'] for r in rs} == {SEED_MAIN}, key
    rows.sort(key=lambda r: (r['k'], r['p'], r['sample_index']))

    # ---- required per-sample CSV (8 columns)
    with open(os.path.join(R, 'random_samples.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['k', 'p', 'seed', 'sample_index', 'outcome', 'onset_step', 'direction', 'steps_simulated'])
        for r in rows:
            w.writerow([r['k'], r['p'], r['seed'], r['sample_index'], r['outcome'], r['onset_step'], r['direction'], r['steps_simulated']])

    # ---- per-cell aggregates
    per_cell = []
    for (k, p) in sorted(cells):
        rs = cells[(k, p)]
        n = len(rs)
        cert = [r for r in rs if r['outcome'] == 'certified']
        outc = {o: sum(1 for r in rs if r['outcome'] == o) for o in ('certified', 'cap', 'boundary', 'nontravel')}
        dirs = {}
        for r in cert: dirs[r['direction']] = dirs.get(r['direction'], 0) + 1
        onsets = [r['onset_step'] for r in cert]
        rmax = max(cert, key=lambda r: r['onset_step']) if cert else None
        per_cell.append({
            'k': k, 'p': p, 'count': n,
            'n_certified': outc['certified'], 'n_cap': outc['cap'], 'n_boundary': outc['boundary'], 'n_nontravel': outc['nontravel'],
            'frac_certified': outc['certified'] / n, 'frac_cap': outc['cap'] / n, 'frac_boundary': outc['boundary'] / n,
            'frac_nontravel': outc['nontravel'] / n,
            'onset_step': stats_of(onsets),
            'mean_n_black': float(np.mean([r['n_black'] for r in rs])),
            'expected_n_black': k * k * p,
            'direction_counts': dirs,
            'n_displacement_not_pm2_pm2': sum(1 for r in cert if abs(r['dispx']) != 2 or abs(r['dispy']) != 2),
            'periods_verified_min': min(r['periods_verified'] for r in cert) if cert else None,
            'max_steps_simulated': max(r['steps_simulated'] for r in rs),
            'max_abs_final_coord': max(max(abs(r['fx']), abs(r['fy'])) for r in rs),
            'longest': {'sample_index': rmax['sample_index'], 'onset_step': rmax['onset_step'], 'direction': rmax['direction'],
                        'n_black': rmax['n_black']} if rmax else None,
        })

    # ---- totals and longest onset overall
    total = len(rows)
    n_cert = sum(1 for r in rows if r['outcome'] == 'certified')
    n_cap = sum(1 for r in rows if r['outcome'] == 'cap')
    n_bound = sum(1 for r in rows if r['outcome'] == 'boundary')
    n_nontr = sum(1 for r in rows if r['outcome'] == 'nontravel')
    specials = [r for r in rows if r['outcome'] != 'certified']
    longest = max((r for r in rows if r['outcome'] == 'certified'), key=lambda r: r['onset_step'])
    # independent re-run of that single sample to get the cell list and confirm the numbers
    out = subprocess.run([os.path.join(D, 'randexp'), 'one', str(longest['k']), str(longest['p']), str(longest['seed']),
                          str(longest['sample_index']), str(CAP)], capture_output=True, text=True, check=True).stdout
    rerun = json.loads(out)
    assert rerun['onset_step'] == longest['onset_step'] and rerun['steps_simulated'] == longest['steps_simulated'] \
        and rerun['direction'] == longest['direction'] and rerun['n_black'] == longest['n_black'], (rerun, longest)
    longest_json = {
        'experiment': 'random', 'conventions': 'CONVENTIONS.md',
        'description': 'Configuration with the longest certified highway onset among the main sweep (%d random configurations, seed %d).' % (total, SEED_MAIN),
        'k': longest['k'], 'p': longest['p'], 'seed': longest['seed'], 'sample_index': longest['sample_index'],
        'n_black': longest['n_black'], 'onset_step': longest['onset_step'], 'direction': longest['direction'],
        'displacement_per_period': [longest['dispx'], longest['dispy']],
        'certification_step': longest['steps_simulated'], 'periods_verified_at_certification': longest['periods_verified'],
        'bbox_pre_onset': {'xmin': longest['bx0'], 'ymin': longest['by0'], 'xmax': longest['bx1'], 'ymax': longest['by1']},
        'final_position': [longest['fx'], longest['fy']],
        'reproduce': './randexp one %d %g %d %d %d' % (longest['k'], longest['p'], longest['seed'], longest['sample_index'], CAP),
        'black_cells': rerun['black_cells'],
    }
    json.dump(longest_json, open(os.path.join(R, 'random_longest.json'), 'w'), indent=1)

    # ---- scaling with k (main sweep, p = 0.5)
    scaling = {}
    for p in PS:
        cs = [c for c in per_cell if c['p'] == p]
        ks = [c['k'] for c in cs]
        scaling['p=%g' % p] = {
            'k': ks,
            'median': [c['onset_step']['median'] for c in cs],
            'mean': [c['onset_step']['mean'] for c in cs],
            'p90': [c['onset_step']['percentiles']['90'] for c in cs],
            'max': [c['onset_step']['max'] for c in cs],
            'fit_median_vs_k_all_k': fit_loglog(ks, [c['onset_step']['median'] for c in cs]),
            'fit_median_vs_k_k_ge_24': fit_loglog([c['k'] for c in cs if c['k'] >= 24], [c['onset_step']['median'] for c in cs if c['k'] >= 24]),
            'fit_mean_vs_k_all_k': fit_loglog(ks, [c['onset_step']['mean'] for c in cs]),
            'fit_mean_vs_k_k_ge_24': fit_loglog([c['k'] for c in cs if c['k'] >= 24], [c['onset_step']['mean'] for c in cs if c['k'] >= 24]),
        }
    # all 40 cells: median onset vs mean number of black cells
    nb = [c['mean_n_black'] for c in per_cell]; med = [c['onset_step']['median'] for c in per_cell]
    scaling['all_cells_median_vs_n_black'] = fit_loglog(nb, med)
    big = [c for c in per_cell if c['k'] >= 24]
    scaling['cells_k_ge_24_median_vs_n_black'] = fit_loglog([c['mean_n_black'] for c in big], [c['onset_step']['median'] for c in big])
    scaling['cells_k_ge_24_median_vs_k_all_p_pooled'] = fit_loglog([c['k'] for c in big], [c['onset_step']['median'] for c in big])

    # ---- extended aggregate-only sweeps (if present)
    def load_stats_dir(sub):
        out = []
        for fn in sorted(glob.glob(os.path.join(D, 'out', sub, '*_summary.jsonl'))):
            for line in open(fn):
                s = json.loads(line)
                pre = fn[:-len('_summary.jsonl')]
                a = np.fromfile(pre + '.u32', dtype=np.uint32).astype(np.int64)
                assert len(a) == s['n_certified'], (fn, len(a), s['n_certified'])
                s['onset_step'] = stats_of(a)
                s['n_special_lines'] = sum(1 for _ in open(pre + '_special.txt'))
                out.append(s)
        out.sort(key=lambda s: (s['k'], s['p']))
        return out
    ext = load_stats_dir('ext'); scale = load_stats_dir('scale'); pfine = load_stats_dir('pfine')
    ext_section = None
    if ext:
        tot = sum(s['n'] for s in ext); cert = sum(s['n_certified'] for s in ext)
        lm = max(ext, key=lambda s: s['s_max'])
        ext_section = {'description': 'same 8x5 (k,p) grid, 100000 samples per cell, seed 20260920, aggregate-only (onset lists in out/ext/*.u32)',
                       'total_configurations': tot, 'total_certified': cert,
                       'total_cap': sum(s['n_cap'] for s in ext), 'total_boundary': sum(s['n_boundary'] for s in ext),
                       'total_nontravel': sum(s['n_nontravel'] for s in ext),
                       'longest_onset': {'k': lm['k'], 'p': lm['p'], 'seed': lm['seed'], 'sample_index': lm['argmax_sample_index'], 'onset_step': lm['s_max'],
                                         'reproduce': './randexp one %d %g %d %d %d' % (lm['k'], lm['p'], lm['seed'], lm['argmax_sample_index'], CAP)},
                       'cells': ext}
        for p in PS:
            cs = [s for s in ext if s['p'] == p]
            ext_section['fit_median_vs_k_p=%g_all_k' % p] = fit_loglog([s['k'] for s in cs], [s['onset_step']['median'] for s in cs])
            ext_section['fit_median_vs_k_p=%g_k_ge_24' % p] = fit_loglog([s['k'] for s in cs if s['k'] >= 24], [s['onset_step']['median'] for s in cs if s['k'] >= 24])
    scale_section = None
    if scale:
        ks = [s['k'] for s in scale]; meds = [s['onset_step']['median'] for s in scale]; means = [s['onset_step']['mean'] for s in scale]
        scale_section = {'description': 'p=0.5, k from 5 to 512, 10000 samples per k, seed 20260921, aggregate-only',
                         'k': ks, 'median': meds, 'mean': means, 'max': [s['s_max'] for s in scale], 'min': [s['s_min'] for s in scale],
                         'p90': [s['onset_step']['percentiles']['90'] for s in scale],
                         'p99': [s['onset_step']['percentiles']['99'] for s in scale],
                         'total_configurations': sum(s['n'] for s in scale), 'total_certified': sum(s['n_certified'] for s in scale),
                         'total_cap': sum(s['n_cap'] for s in scale), 'total_boundary': sum(s['n_boundary'] for s in scale),
                         'total_nontravel': sum(s['n_nontravel'] for s in scale),
                         'fit_median_vs_k_all': fit_loglog(ks, meds),
                         'fit_median_vs_k_k_ge_64': fit_loglog([k for k in ks if k >= 64], [m for k, m in zip(ks, meds) if k >= 64]),
                         'fit_mean_vs_k_k_ge_64': fit_loglog([k for k in ks if k >= 64], [m for k, m in zip(ks, means) if k >= 64]),
                         'fit_median_vs_n_black_k_ge_64': fit_loglog([s['mean_n_black'] for s in scale if s['k'] >= 64], [s['onset_step']['median'] for s in scale if s['k'] >= 64]),
                         'cells': scale}
    pfine_section = None
    if pfine:
        pfine_section = {'description': 'k=32, p from 0.05 to 0.95 step 0.05, 10000 samples per p, seed 20260922, aggregate-only',
                         'p': [s['p'] for s in pfine], 'median': [s['onset_step']['median'] for s in pfine],
                         'mean': [s['onset_step']['mean'] for s in pfine], 'max': [s['s_max'] for s in pfine],
                         'total_configurations': sum(s['n'] for s in pfine), 'total_certified': sum(s['n_certified'] for s in pfine),
                         'cells': pfine}

    verify = None
    vp = os.path.join(D, 'out', 'verify_py.json')
    if os.path.exists(vp): verify = json.load(open(vp))

    grand_total = total + (ext_section['total_configurations'] if ext_section else 0) + (scale_section['total_configurations'] if scale_section else 0) + (pfine_section['total_configurations'] if pfine_section else 0)
    grand_cert = n_cert + (ext_section['total_certified'] if ext_section else 0) + (scale_section['total_certified'] if scale_section else 0) + (pfine_section['total_certified'] if pfine_section else 0)

    # verdict on polynomial growth
    fit_scale = scale_section['fit_median_vs_k_k_ge_64'] if scale_section else None
    result = {
        'experiment': 'random',
        'conventions': 'CONVENTIONS.md',
        'description': "Random initial configurations in a k x k box with density p (CONVENTIONS.md), ant at (0,0) facing North, run until the 104-step highway is certified or a step cap is hit.",
        'parameters': {
            'k_values': KS, 'p_values': PS, 'samples_per_cell_main': 10000, 'seed_main': SEED_MAIN, 'step_cap': CAP,
            'grid': '4096x4096 byte grid, origin at (2048,2048); a run touching the outermost ring is reported as outcome=boundary',
            'sampling_scheme': 'cells visited in order i=0..k*k-1, (x,y)=(xmin+i%k, xmin+i//k), xmin=-(k//2); splitmix64 with state seed*0x9E3779B97F4A7C15 + sample_index*0xBF58476D1CE4E5B9 + k*0x94D049BB133111EB + round(1000p)*0xD6E8FEB86659FD93 (mod 2^64); cell black iff (r>>11)*2^-53 < p. Every sample is regenerable from (k,p,seed,sample_index): ./randexp dump k p seed sample_index',
            'onset_step_definition': 's = max{k>=1 : t[k] != t[k+104]} (0 if no mismatch); t[k]=R if step k turned right (cell white)',
            'certification': 'stop at the first step n >= s+2184 (t[k]==t[k+104] verified for all k in s+1..n-104, i.e. >= 20 full periods) at which the ant is >= 20 cells beyond the bounding box of {origin, initial black cells, cells modified in steps 1..s} in both coordinates in its travel direction (sign of pos(n)-pos(n-104), both components nonzero). Identical rule to research/exhaustive.',
            'outcomes': {'certified': 'highway certified', 'cap': 'step cap reached, turns not 104-periodic for 20 periods', 'boundary': 'ant reached the grid edge (reported, never wrapped)', 'nontravel': 'cap reached while turns were 104-periodic but the period displacement had a zero component or the escape margin was never reached'},
            'simulator': 'research/random/randexp.c (gcc -O3 -march=native), ~70-100 Msteps/s',
            'cross_check': 'research/random/verify_py.py: independent pure-Python RNG + ant + onset + certification on a subset of samples',
            'parallelism': '2 processes (k in {5,12,24,48} and k in {8,16,32,64})',
        },
        'results': {
            'totals_main_sweep': {'total_configurations': total, 'total_certified_highway': n_cert, 'total_cap': n_cap, 'total_boundary': n_bound,
                                  'total_nontravel': n_nontr, 'fraction_certified': n_cert / total,
                                  'total_steps_simulated': sum(r['steps_simulated'] for r in rows),
                                  'max_steps_simulated_single_run': max(r['steps_simulated'] for r in rows),
                                  'max_abs_coordinate_reached': max(max(abs(r['fx']), abs(r['fy'])) for r in rows),
                                  'n_displacement_not_pm2_pm2': sum(1 for r in rows if r['outcome'] == 'certified' and (abs(r['dispx']) != 2 or abs(r['dispy']) != 2)),
                                  'direction_counts': {d: sum(1 for r in rows if r['direction'] == d) for d in ('+x,+y', '+x,-y', '-x,+y', '-x,-y')},
                                  'onset_step_all_certified': stats_of([r['onset_step'] for r in rows if r['outcome'] == 'certified'])},
            'longest_onset_main_sweep': {k: v for k, v in longest_json.items() if k != 'black_cells'},
            'non_certified_samples_main_sweep': [{c: r[c] for c in COLS} for r in specials],
            'per_cell': per_cell,
            'scaling_main_sweep': scaling,
            'extended_sweep': ext_section,
            'scaling_sweep_p05': scale_section,
            'density_sweep_k32': pfine_section,
            'grand_totals_all_sweeps': {'total_configurations': grand_total, 'total_certified': grand_cert,
                                        'total_non_certified': grand_total - grand_cert},
            'python_cross_check': verify,
        },
        'notes': [
            'Main sweep: 8 k-values x 5 densities x 10000 samples = 400000 configurations, every one certified (see totals).',
            'Onset statistics are over certified samples only (all samples in every cell were certified, so this is the full cell).',
            'For small boxes (k<=12) the onset distribution resembles the empty-grid case (s=9977 for the empty grid); for large k the onset is dominated by the time the ant needs to leave the random box; the fitted median grows about like k^1.14 over k=64..512 at p=0.5 (far slower than a diffusive k^2), a finite-range fit, not an asymptotic law: see scaling fits.',
            'median uses numpy.median (average of the two middle values for even counts); percentiles use the lower-order statistic.',
        ],
    }
    if fit_scale:
        result['notes'].append('Scaling verdict: over k=64..512 at p=0.5 the median onset grows as k^%.2f (least squares on logs), i.e. as N^%.2f in the number of black cells N=k^2 p -- roughly the square root of N, far below linear in N and nowhere near exponential: the data suggest polynomial (in fact sub-linear in N, near-linear in k) growth of the typical onset.' % (fit_scale['exponent'], scale_section['fit_median_vs_n_black_k_ge_64']['exponent']))
        result['notes'].append('Even the per-cell maximum over 10000 samples grows only from 1.7e5 (k=5) to 1.3e6 (k=512) steps; the longest run in any sweep used 1,337,591 of the 2e7-step cap (6.7%).')
    json.dump(result, open(os.path.join(R, 'random.json'), 'w'), indent=1)

    # ---- console summary
    print('main sweep: %d configs, %d certified, %d cap, %d boundary, %d nontravel' % (total, n_cert, n_cap, n_bound, n_nontr))
    print('longest onset: k=%d p=%g idx=%d s=%d dir=%s n_black=%d cert_step=%d' % (longest['k'], longest['p'], longest['sample_index'], longest['onset_step'], longest['direction'], longest['n_black'], longest['steps_simulated']))
    print('%4s %5s %6s %6s %8s %10s %8s %8s' % ('k', 'p', 'n', 'min', 'mean', 'median', 'p90', 'max'))
    for c in per_cell:
        o = c['onset_step']
        print('%4d %5g %6d %6d %8.1f %10.1f %8d %8d  cert=%.4f cap=%d bound=%d' % (c['k'], c['p'], c['count'], o['min'], o['mean'], o['median'], o['percentiles']['90'], o['max'], c['frac_certified'], c['n_cap'], c['n_boundary']))
    for p in PS:
        s = scaling['p=%g' % p]
        print('p=%g: median vs k exponent (all k) %.3f, (k>=24) %.3f; mean exponent (k>=24) %.3f' % (p, s['fit_median_vs_k_all_k']['exponent'], s['fit_median_vs_k_k_ge_24']['exponent'], s['fit_mean_vs_k_k_ge_24']['exponent']))
    if ext_section: print('extended: %d configs, %d certified; longest s=%d at k=%d p=%g idx=%d' % (ext_section['total_configurations'], ext_section['total_certified'], ext_section['longest_onset']['onset_step'], ext_section['longest_onset']['k'], ext_section['longest_onset']['p'], ext_section['longest_onset']['sample_index']))
    if scale_section:
        print('scale p=0.5: k', scale_section['k']); print('  median', scale_section['median']); print('  mean', [round(m) for m in scale_section['mean']]); print('  max', scale_section['max'])
        print('  fit median~k^b: all %.3f, k>=64 %.3f; mean k>=64 %.3f; median~N^b k>=64 %.3f' % (scale_section['fit_median_vs_k_all']['exponent'], scale_section['fit_median_vs_k_k_ge_64']['exponent'], scale_section['fit_mean_vs_k_k_ge_64']['exponent'], scale_section['fit_median_vs_n_black_k_ge_64']['exponent']))
    if pfine_section:
        print('pfine k=32: p', pfine_section['p']); print('  median', pfine_section['median'])
    print('grand total: %d configs, %d certified' % (grand_total, grand_cert))
    if verify: print('python cross-check:', verify)

if __name__ == '__main__':
    main()
