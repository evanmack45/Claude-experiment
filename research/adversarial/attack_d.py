#!/usr/bin/env python3
"""Attack D (bonus): greedy obstacle CHAINING inside a bounded box.
Start from the empty grid. Repeatedly: simulate (antsim), locate the certified
highway, and place a small obstacle (2x2 block) on its future path among untouched
cells inside the box |x|,|y| <= B; among ~35 candidate positions along one period
(different phases, minimal distance) keep the one giving the LONGEST onset of the
new configuration (each candidate is a full from-scratch simulation). Stop when no
candidate fits in the box (the final highway leaves the box) or a candidate fails
to certify. Every stage's configuration is a genuine initial configuration.
Usage: python3 attack_d.py [B=100] [max_stages=60]
Writes out/attack_d.jsonl (one line per stage) and out/attack_d_final.cfg."""
import json, os, subprocess, sys, time
here = os.path.dirname(os.path.abspath(__file__))
B = int(sys.argv[1]) if len(sys.argv) > 1 else 100
MAXST = int(sys.argv[2]) if len(sys.argv) > 2 else 60
SHAPE = [(0, 0), (1, 0), (0, 1), (1, 1)]
DX = [0, 1, 0, -1]; DY = [1, 0, -1, 0]
proc = subprocess.Popen([os.path.join(here, 'antsim'), 'batch', '--cap', '50000000', '--grid', '8192'],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
def evaluate(cfgs):
    for c in cfgs: proc.stdin.write(' '.join(f'{x},{y}' for x, y in c) + '\n')
    proc.stdin.flush(); return [json.loads(proc.stdout.readline()) for _ in cfgs]
def pysim(cfg, N):
    black = set(map(tuple, cfg)); touched = set(black); x = y = d = 0; pos = [(0, 0)]
    for k in range(N):
        if (x, y) in black: d = (d + 3) % 4; black.discard((x, y))
        else: d = (d + 1) % 4; black.add((x, y))
        touched.add((x, y)); x += DX[d]; y += DY[d]; pos.append((x, y))
    return pos, touched
cfg = []; stages = []; t0 = time.time()
log = open(os.path.join(here, 'out', 'attack_d.jsonl'), 'w')
for stage in range(MAXST):
    r = evaluate([cfg])[0]
    assert r['outcome'] == 'certified', r
    c = r['cert_step']; disp = tuple(r['disp'])
    pos, touched = pysim(cfg, c + 104)
    cands = []
    for i in range(0, 104, 3):
        base = pos[c + i]
        for m in range(0, 400):
            anchor = (base[0] + m * disp[0], base[1] + m * disp[1])
            cells = [(anchor[0] + sx, anchor[1] + sy) for sx, sy in SHAPE]
            if any(abs(cx) > B or abs(cy) > B for cx, cy in cells): break
            if any(cl in touched for cl in cells): continue
            cands.append((i, m, cells)); break
    if not cands:
        stages.append(dict(stage=stage, onset_step=r['onset_step'], direction=r['direction'], n_black=len(cfg), note='highway leaves the box: no candidate placement fits', cells=cfg))
        log.write(json.dumps(stages[-1]) + '\n'); break
    rs = evaluate([cfg + cells for _, _, cells in cands])
    ok = [(rr, cd) for rr, cd in zip(rs, cands) if rr['outcome'] == 'certified' and rr['first_initial_black_read'] > 0]
    ncap = sum(rr['outcome'] != 'certified' for rr in rs)
    if not ok:
        stages.append(dict(stage=stage, onset_step=r['onset_step'], direction=r['direction'], n_black=len(cfg), note=f'no certified candidate ({ncap} non-certified)', cells=cfg, noncert=[rr for rr in rs if rr['outcome'] != 'certified']))
        log.write(json.dumps(stages[-1]) + '\n'); break
    bi = max(range(len(ok)), key=lambda j: ok[j][0]['onset_step'])
    br, (i, m, cells) = ok[bi]
    st = dict(stage=stage, prev_onset=r['onset_step'], prev_direction=r['direction'], prev_cert_step=c,
              n_candidates=len(cands), n_candidates_certified=len(ok), n_candidates_noncertified=ncap,
              candidate_onsets_min=min(rr['onset_step'] for rr, _ in ok), candidate_onsets_max=br['onset_step'],
              chosen_phase=i, chosen_periods_ahead=m, obstacle=cells, contact_step=br['first_initial_black_read'],
              new_onset=br['onset_step'], new_direction=br['direction'], extra_chaos=br['onset_step'] - br['first_initial_black_read'],
              n_black=len(cfg) + len(cells), elapsed_s=round(time.time() - t0, 1))
    stages.append(st); log.write(json.dumps(st) + '\n'); log.flush()
    print(f"stage {stage}: onset {r['onset_step']} -> {br['onset_step']} (contact {br['first_initial_black_read']}, extra {st['extra_chaos']}, dir {br['direction']}, {len(ok)}/{len(cands)} cert, {ncap} noncert) {st['elapsed_s']}s", file=sys.stderr)
    cfg = cfg + cells
final = evaluate([cfg])[0]
open(os.path.join(here, 'out', 'attack_d_final.cfg'), 'w').write(f'# Attack D chained obstacles, box |x|,|y|<={B}\n' + ''.join(f'{x} {y}\n' for x, y in cfg))
summary = dict(box_halfwidth=B, n_stages=len([s for s in stages if 'new_onset' in s]), n_black=len(cfg), final=final,
               final_onset=final['onset_step'], ratio_to_empty=final['onset_step'] / 9977, stages=stages, cells=cfg,
               total_noncertified_candidates=sum(s.get('n_candidates_noncertified', 0) for s in stages), elapsed_s=time.time() - t0)
json.dump(summary, open(os.path.join(here, 'out', 'attack_d_summary.json'), 'w'), indent=1)
print(json.dumps({k: v for k, v in summary.items() if k not in ('stages', 'cells', 'final')}))
