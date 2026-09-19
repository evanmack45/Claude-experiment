#!/usr/bin/env python3
"""Recount the archived Attack-B evolutionary-search evidence in evidence/*.csv.gz and
spot-check it by re-simulation.

Prints, per run and in total: evaluations, non-certified evaluations, distinct genomes, the best
onset, and re-simulates N random rows (default 200; --n 0 to skip) with ./antsim, checking that
each row's recorded onset and outcome reproduce.  Exit status 1 on any mismatch.

Usage: python3 count_evidence.py [--n 200] [--seed 1]
"""
import argparse, csv, glob, gzip, io, json, os, random, subprocess, sys

here = os.path.dirname(os.path.abspath(__file__))
K = 12; LO = -(K // 2); NCELL = K * K


def cells_of_hex(h):
    bits = bin(int(h, 16))[2:].zfill(NCELL)
    return [(LO + i % K, LO + i // K) for i in range(NCELL) if bits[i] == '1']


ap = argparse.ArgumentParser(); ap.add_argument('--n', type=int, default=200); ap.add_argument('--seed', type=int, default=1)
a = ap.parse_args()
total = nc_total = 0; best = (0, None); all_genomes = set(); sample_pool = []
for fn in sorted(glob.glob(os.path.join(here, 'evidence', 'attack_b_*.csv.gz'))):
    name = os.path.basename(fn)[len('attack_b_'):-7]
    rows = list(csv.DictReader(io.TextIOWrapper(gzip.open(fn, 'rb'))))
    genomes = {r['genome_hex'] for r in rows}; all_genomes |= genomes
    nc = sum(r['outcome'] != 'certified' for r in rows)
    b = max(rows, key=lambda r: int(r['onset']))
    total += len(rows); nc_total += nc
    if int(b['onset']) > best[0]: best = (int(b['onset']), name)
    summ = json.load(open(fn[:-7] + '_summary.json'))
    ok = summ['evals'] == len(rows) and summ['n_non_certified'] == nc and summ['best_onset'] == int(b['onset'])
    print(f"{name}: {len(rows)} evaluations, {nc} non-certified, {len(genomes)} distinct genomes, best onset {b['onset']}"
          f" | summary agrees: {ok}")
    if not ok: sys.exit(1)
    sample_pool += [(name, r) for r in rows]
print(f"TOTAL: {total} evaluations, {nc_total} non-certified, {len(all_genomes)} distinct genomes, best onset {best[0]} ({best[1]})")
if a.n > 0:
    exe = os.path.join(here, 'antsim')
    if not os.path.exists(exe):
        subprocess.run(['gcc', '-O3', '-march=native', '-o', exe, os.path.join(here, 'antsim.c')], check=True)
    rng = random.Random(a.seed); bad = 0
    for name, r in rng.sample(sample_pool, a.n):
        cfg = os.path.join(here, 'out', 'count_evidence_tmp.cfg'); os.makedirs(os.path.dirname(cfg), exist_ok=True)
        open(cfg, 'w').write(''.join(f'{x} {y}\n' for x, y in cells_of_hex(r['genome_hex'])))
        res = json.loads(subprocess.run([exe, 'run', cfg, '--cap', '50000000', '--grid', '8192'], capture_output=True, text=True).stdout)
        if res['onset_step'] != int(r['onset']) or res['outcome'] != r['outcome']:
            bad += 1; print('MISMATCH', name, r['eval'], r['onset'], res['onset_step'], res['outcome'])
    print(f"re-simulated {a.n} random rows: {a.n - bad} reproduce, {bad} mismatches")
    sys.exit(1 if bad else 0)
