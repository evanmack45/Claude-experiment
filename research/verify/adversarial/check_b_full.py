#!/usr/bin/env python3
"""Re-simulate ALL rows of the two main-run CSVs and a 20,000-row seeded sample of each extended CSV with
./vsim; count distinct genomes across all Attack-B logs and distinct configurations across attacks A-D."""
import csv, json, os, random, subprocess, hashlib
here=os.path.dirname(os.path.abspath(__file__)); od=os.path.join(here,'..','..','adversarial','out')
def cells(h):
    bits=bin(int(h,16))[2:].zfill(144); return [(-6+i%12, -6+i//12) for i in range(144) if bits[i]=='1']
def resim(rows, idx):
    inp='\n'.join(' '.join(f'{x} {y}' for x,y in cells(rows[i][5])) for i in idx)+'\n'
    out=[json.loads(l) for l in subprocess.run([os.path.join(here,'vsim'),'batch'], input=inp, capture_output=True, text=True).stdout.strip().split('\n')]
    return sum(1 for i,o in zip(idx,out) if o['onset']!=int(rows[i][2]) or o['outcome']!='certified')
rng=random.Random(777); rep={}
for name in ('main_seed1','main_seed2','ext_seed11','ext_seed12'):
    rows=[r for r in csv.reader(open(os.path.join(od,f'attack_b_{name}.csv')))][1:]
    idx = list(range(len(rows))) if name.startswith('main') else sorted(rng.sample(range(len(rows)), 20000))
    bad=resim(rows, idx); rep[name]=dict(n_rows=len(rows), n_resimulated=len(idx), n_mismatch=bad); print(name, rep[name])
json.dump(rep, open(os.path.join(here,'out','check_b_full.json'),'w'), indent=1)
