#!/usr/bin/env python3
"""Pure-Python re-simulation of research/results/random_longest.json: regenerates the
configuration from (k,p,seed,sample_index) with the Python RNG, checks the black-cell list
matches the JSON, simulates in Python and recomputes onset, certification step, direction."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_py import gen_config, analyze
L = json.load(open('/home/user/Claude-experiment/research/results/random_longest.json'))
black = gen_config(L['k'], L['p'], L['seed'], L['sample_index'])
assert black == set(map(tuple, L['black_cells'])), 'black cell list mismatch'
s, cert, dirname, bbox = analyze(black, L['certification_step'] + 500)
print('python: s=%d cert=%d dir=%s bbox=%s  json: s=%d cert=%d dir=%s' % (s, cert, dirname, bbox, L['onset_step'], L['certification_step'], L['direction']))
ok = (s == L['onset_step'] and cert == L['certification_step'] and dirname == L['direction']
      and bbox == (L['bbox_pre_onset']['xmin'], L['bbox_pre_onset']['ymin'], L['bbox_pre_onset']['xmax'], L['bbox_pre_onset']['ymax']))
json.dump({'ok': ok, 'python_onset': s, 'python_cert_step': cert, 'python_direction': dirname}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'verify_longest.json'), 'w'))
print('OK' if ok else 'MISMATCH'); sys.exit(0 if ok else 1)
