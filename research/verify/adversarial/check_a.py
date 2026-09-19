#!/usr/bin/env python3
"""Independent re-derivation of Attack A (verify/adversarial). Regenerates the 1512 placements from the
finder's stated rule using MY OWN pure-Python empty-grid simulation, compares the cell lists with the
finder's out/attack_a.jsonl, re-simulates all placements with ./vsim batch and compares onset/contact/
direction per placement, then recomputes every statistic in claims C4-C6."""
import json, subprocess, os, statistics, sys
here = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(here, '..', '..', 'adversarial', 'out', 'attack_a.jsonl')
DX=[0,1,0,-1]; DY=[1,0,-1,0]; black=set(); x=y=d=0; pos=[(0,0)]; t=[None]
for k in range(1, 13000):
    if (x,y) in black: d=(d-1)%4; black.discard((x,y)); t.append('L')
    else: d=(d+1)%4; black.add((x,y)); t.append('R')
    x+=DX[d]; y+=DY[d]; pos.append((x,y))
s = max(k for k in range(1, len(t)-104) if t[k]!=t[k+104]); assert s == 9977, s
P0 = pos[12680]; disp = (pos[12784][0]-P0[0], pos[12784][1]-P0[1]); print('P0', P0, 'disp', disp)
SHAPES = {'1x1':[(0,0)], '2x2':[(0,0),(1,0),(0,1),(1,1)], '3x3':[(i,j) for i in range(3) for j in range(3)],
          'hline5':[(i,0) for i in range(5)], 'vline5':[(0,i) for i in range(5)], 'L3':[(0,0),(1,0),(2,0),(0,1),(0,2)]}
DIST=[0,1,2,3,5,8,13,21,34,55,89,144,233,377]; LAT=list(range(-8,9,2)); PH=[0,1]
mine=[]
for sh,cells in SHAPES.items():
    for m in DIST:
        for dv in LAT:
            for ph in PH:
                ax = P0[0] + m*disp[0] + dv - ph; ay = P0[1] + m*disp[1] - dv - ph
                mine.append(dict(shape=sh, m=m, dv=dv, ph=ph, cells=[[ax+cx, ay+cy] for cx,cy in cells]))
theirs=[json.loads(l) for l in open(F)]
assert len(theirs)==1512 and len(mine)==1512
cellmatch = sum(a['cells']==b['cells'] and a['shape']==b['shape'] and a['m']==b['periods_ahead'] and a['dv']==b['lateral'] and a['ph']==b['phase'] for a,b in zip(mine,theirs))
print('placements with identical cells/metadata:', cellmatch, '/ 1512')
inp='\n'.join(' '.join(f'{c[0]} {c[1]}' for c in p['cells']) for p in mine)+'\n'
out=subprocess.run([os.path.join(here,'vsim'),'batch'], input=inp, capture_output=True, text=True).stdout.strip().split('\n')
assert len(out)==1512
res=[json.loads(l) for l in out]
mism=[]
for i,(r,th) in enumerate(zip(res,theirs)):
    if r['outcome']!='certified' or r['onset']!=th['onset_step'] or r['contact']!=th['first_initial_black_read'] or r['direction']!=th['direction']:
        mism.append((i, r, {k:th[k] for k in ('outcome','onset_step','first_initial_black_read','direction')}))
print('per-placement mismatches (onset/contact/direction/outcome):', len(mism)); print(mism[:5])
print('all certified (mine):', all(r['outcome']=='certified' for r in res), 'max cert_step', max(r['cert_step'] for r in res))
hit=[(p,r) for p,r in zip(mine,res) if r['contact']>0]; miss=[r for r in res if r['contact']==0]
print('hits', len(hit), 'misses', len(miss), 'miss onsets', sorted(set(r['onset'] for r in miss)))
dirs={}
for p,r in hit: dirs[r['direction']]=dirs.get(r['direction'],0)+1
print('directions after hit', dirs)
ex=sorted(r['onset']-r['contact'] for p,r in hit)
q=lambda v,p: v[min(len(v)-1,int(p*len(v)))]
print('extra chaos: min', ex[0], 'median', statistics.median(ex), 'mean %.3f'%statistics.mean(ex), 'p90(idx floor)', q(ex,.9), 'p90(nearest-rank)', ex[max(0,-(-9*len(ex)//10)-1)], 'max', ex[-1])
print('frac extra<9977: %.4f'%(sum(e<9977 for e in ex)/len(ex)), 'frac extra<=9977: %.4f'%(sum(e<=9977 for e in ex)/len(ex)))
b=max(zip(mine,res), key=lambda pr: pr[1]['onset']); print('longest onset', b[1], b[0])
print('max steps to certify (my cert_step max)', max(r['cert_step'] for r in res))
# lower bound check: is onset >= 12680+104m for every hit? and contact >= 12680+104m?
viol=[(p['m'],r['contact'],r['onset']) for p,r in hit if r['onset'] < 12680+104*p['m']]
print('hits with onset < 12680+104m:', len(viol), viol[:5])
viol2=[(p['m'],r['contact']) for p,r in hit if r['contact'] < 12680+104*p['m']]
print('hits with contact < 12680+104m:', len(viol2), 'e.g.', viol2[:3])
json.dump(dict(cellmatch=cellmatch, mismatches=len(mism), hits=len(hit), misses=len(miss), dirs=dirs, extra=dict(min=ex[0],median=statistics.median(ex),mean=statistics.mean(ex),p90=q(ex,.9),max=ex[-1]), longest=b[1], longest_meta=b[0]), open(os.path.join(here,'out','check_a.json'),'w'), indent=1)
