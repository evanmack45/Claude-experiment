#!/usr/bin/env python3
"""Recompute Attack-B CSV statistics (row counts, max, mean, non-certified) for all four logs, check the
genome-hex decoding convention, and re-simulate a seeded random subset of rows with ./vsim (exact onset match)."""
import csv, json, os, random, subprocess, statistics, sys
here=os.path.dirname(os.path.abspath(__file__)); od=os.path.join(here,'..','..','adversarial','out')
K=12; LO=-6
def cells(h):
    bits=bin(int(h,16))[2:].zfill(144); return [(LO+i%K, LO+i//K) for i in range(144) if bits[i]=='1']
NS=int(sys.argv[1]) if len(sys.argv)>1 else 1500
rng=random.Random(20260919); summary={}
for name in ('main_seed1','main_seed2','ext_seed11','ext_seed12'):
    rows=[]; 
    with open(os.path.join(od,f'attack_b_{name}.csv')) as f:
        rd=csv.reader(f); hdr=next(rd)
        for r in rd: rows.append(r)
    on=[int(r[2]) for r in rows]; nc=sum(r[3]!='certified' for r in rows)
    evals=[int(r[0]) for r in rows]; contiguous = evals==list(range(1,len(rows)+1))
    bi=max(range(len(on)), key=lambda i:on[i])
    nb_ok = all(int(r[4])==len(cells(r[5])) for r in rows[:2000])
    st=dict(n_rows=len(rows), eval_ids_contiguous=contiguous, max=on[bi], best_eval=evals[bi], best_cells=cells(rows[bi][5]), mean=statistics.mean(on), median=statistics.median(on), n_noncert=nc, n_above_200k=sum(v>200000 for v in on), nblack_col_matches_hex_first2000=nb_ok)
    # re-simulate a random subset + the best row
    idx=sorted(rng.sample(range(len(rows)), min(NS,len(rows)))); 
    if bi not in idx: idx.append(bi)
    inp='\n'.join(' '.join(f'{x} {y}' for x,y in cells(rows[i][5])) for i in idx)+'\n'
    out=[json.loads(l) for l in subprocess.run([os.path.join(here,'vsim'),'batch'], input=inp, capture_output=True, text=True).stdout.strip().split('\n')]
    mism=[(i,int(rows[i][2]),o['onset'],o['outcome']) for i,o in zip(idx,out) if o['onset']!=int(rows[i][2]) or o['outcome']!='certified']
    st.update(n_resimulated=len(idx), n_mismatch=len(mism), mismatches=mism[:10], subset_seed=20260919)
    summary[name]=st; print(name, json.dumps({k:v for k,v in st.items() if k!='best_cells'}))
    print('   best cells', st['best_cells'])
json.dump(summary, open(os.path.join(here,'out','check_b_csv.json'),'w'), indent=1)
