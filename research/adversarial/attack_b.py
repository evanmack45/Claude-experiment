#!/usr/bin/env python3
"""Attack B: (1+lambda) evolutionary hill-climb for the LONGEST highway onset over
initial configurations in the 12x12 box of CONVENTIONS.md (x,y in -6..5).
Mutation: flip r cells, r uniform in {1,2,3}. Acceptance: child onset >= parent
onset (neutral moves allowed). Restart from a fresh random configuration (density
p ~ U(0.2,0.8)) after `stall` evaluations without strict improvement. Objective
= onset step; a non-certified outcome (cap/nontravel/boundary) counts as 10**18.
Evaluations are done by ./antsim batch (cap 50,000,000, grid 8192).

Usage: python3 attack_b.py --seed S --budget N --out PREFIX [--lam 4] [--stall 600] [--start-k5]
Writes PREFIX.csv (one line per evaluation: eval,restart,onset,outcome,nblack,genome_hex)
and PREFIX_summary.json.
"""
import argparse, json, os, random, subprocess, sys, time
ap = argparse.ArgumentParser()
ap.add_argument('--seed', type=int, required=True); ap.add_argument('--budget', type=int, required=True)
ap.add_argument('--out', required=True); ap.add_argument('--lam', type=int, default=4)
ap.add_argument('--stall', type=int, default=600); ap.add_argument('--start-k5', action='store_true')
ap.add_argument('--cap', type=int, default=50000000); ap.add_argument('--time-limit', type=float, default=1e18, help='seconds')
a = ap.parse_args()
here = os.path.dirname(os.path.abspath(__file__))
K = 12; LO = -(K // 2); NCELL = K * K; HUGE = 10**18
def cell_of(i): return (LO + i % K, LO + i // K)
def idx_of(x, y): return (y - LO) * K + (x - LO)
rng = random.Random(a.seed)
proc = subprocess.Popen([os.path.join(here, 'antsim'), 'batch', '--cap', str(a.cap), '--grid', '8192'],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
def evaluate(genomes):
    for g in genomes:
        proc.stdin.write(' '.join(f'{cell_of(i)[0]},{cell_of(i)[1]}' for i in range(NCELL) if g[i]) + '\n')
    proc.stdin.flush()
    out = []
    for g in genomes:
        r = json.loads(proc.stdout.readline())
        r['fitness'] = r['onset_step'] if r['outcome'] == 'certified' else HUGE
        out.append(r)
    return out
def ghex(g): return '%036x' % int(''.join('1' if b else '0' for b in g), 2)
def random_genome():
    p = rng.uniform(0.2, 0.8); return [rng.random() < p for _ in range(NCELL)]
def mutate(g):
    c = list(g)
    for i in rng.sample(range(NCELL), rng.choice((1, 2, 3))): c[i] = not c[i]
    return c
k5 = [(0,-2),(2,-2),(-2,-1),(-1,-1),(2,-1),(0,1),(2,1),(-2,2),(0,2),(1,2),(2,2)]
log = open(a.out + '.csv', 'w'); log.write('eval,restart,onset,outcome,nblack,genome_hex\n')
evals = 0; restart = 0; best = None; ever_cap = []; t0 = time.time(); hist = []
def go(): return evals < a.budget and time.time() - t0 < a.time_limit
while go():
    if a.start_k5 and restart == 0:
        parent = [False] * NCELL
        for x, y in k5: parent[idx_of(x, y)] = True
    else: parent = random_genome()
    pr = evaluate([parent])[0]; evals += 1
    log.write(f"{evals},{restart},{pr['onset_step']},{pr['outcome']},{pr['n_black_init']},{ghex(parent)}\n")
    if pr['outcome'] != 'certified': ever_cap.append(dict(genome=ghex(parent), result=pr))
    if best is None or pr['fitness'] > best['fitness']: best = dict(pr, genome=ghex(parent), eval=evals, restart=restart)
    since = 0
    while go() and since < a.stall:
        kids = [mutate(parent) for _ in range(min(a.lam, a.budget - evals))]
        rs = evaluate(kids)
        improved = False
        for g, r in zip(kids, rs):
            evals += 1
            log.write(f"{evals},{restart},{r['onset_step']},{r['outcome']},{r['n_black_init']},{ghex(g)}\n")
            if r['outcome'] != 'certified': ever_cap.append(dict(genome=ghex(g), result=r))
            if r['fitness'] > best['fitness']: best = dict(r, genome=ghex(g), eval=evals, restart=restart)
        bi = max(range(len(rs)), key=lambda i: rs[i]['fitness'])
        if rs[bi]['fitness'] > pr['fitness']: improved = True
        if rs[bi]['fitness'] >= pr['fitness']: parent, pr = kids[bi], rs[bi]
        since = 0 if improved else since + len(kids)
        if evals % 1000 < len(kids):
            print(f"seed {a.seed} eval {evals} restart {restart} parent {pr['onset_step']} best {best['onset_step']} ({time.time()-t0:.0f}s)", file=sys.stderr)
    hist.append(dict(restart=restart, final_parent_onset=pr['onset_step'], evals_at_end=evals))
    restart += 1
log.close(); proc.stdin.close(); proc.wait()
bg = best['genome']; bits = bin(int(bg, 16))[2:].zfill(NCELL)
cells = [list(cell_of(i)) for i in range(NCELL) if bits[i] == '1']
summary = dict(seed=a.seed, budget=a.budget, time_limit_s=a.time_limit, evals=evals, lam=a.lam, stall=a.stall, start_k5=a.start_k5, cap=a.cap,
               restarts=restart, best_onset=best['onset_step'], best_outcome=best['outcome'], best_direction=best['direction'],
               best_eval=best['eval'], best_restart=best['restart'], best_genome_hex=bg, best_cells=cells, best_result=best,
               n_non_certified=len(ever_cap), non_certified=ever_cap, restart_history=hist, elapsed_s=time.time() - t0)
json.dump(summary, open(a.out + '_summary.json', 'w'), indent=1)
print(json.dumps({k: summary[k] for k in ('seed', 'evals', 'restarts', 'best_onset', 'best_direction', 'best_eval', 'n_non_certified', 'elapsed_s', 'best_cells')}))
