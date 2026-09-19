#!/usr/bin/env python3
"""Compare ./randexp one against the reviewer's independent reference on tiny configs
(k in 1..4, several seeds) including bbox, cert step, direction, final position."""
import subprocess, json, sys
import os
from ref_ant import onset_and_cert
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'random', 'randexp')
cases = [(1, 0, 0, 0), (1, 1, 0, 0)] + [(k, p, 7, i) for k in (2, 3, 4) for p in (0.3, 0.7) for i in range(3)] + [(5, 0.5, 20260919, i) for i in range(4)]
nfail = 0
for (k, p, seed, idx) in cases:
    j = json.loads(subprocess.run([R, 'one', str(k), str(p), str(seed), str(idx), '20000000'], capture_output=True, text=True, check=True).stdout)
    black = set(map(tuple, j['black_cells']))
    ref = onset_and_cert(black, j['steps_simulated'] + 1000)
    same = (ref['s'] == j['onset_step'] and ref['cert'] == j['steps_simulated'] and ref['dir'] == j['direction']
            and list(ref['disp']) == j['disp'] and list(ref['bbox']) == j['bbox_pre_onset'] and list(ref['final']) == j['final_pos'])
    print(f'k={k} p={p} seed={seed} idx={idx} nblack={len(black)}: C s={j["onset_step"]} cert={j["steps_simulated"]} {j["direction"]} bbox={j["bbox_pre_onset"]} | ref s={ref["s"]} cert={ref["cert"]} {ref["dir"]} bbox={list(ref["bbox"])}  {"OK" if same else "MISMATCH"}')
    nfail += (not same)
print(f'{len(cases)} cases, {nfail} mismatches')
sys.exit(1 if nfail else 0)
