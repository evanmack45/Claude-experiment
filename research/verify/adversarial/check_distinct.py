#!/usr/bin/env python3
"""Count distinct configurations (memory-light): Attack-B rows keyed by genome hex (a bijective encoding of the
12x12 box); A/C/D configurations that fit in the box are encoded the same way, others are trivially distinct."""
import csv, json, os
here=os.path.dirname(os.path.abspath(__file__)); od=os.path.join(here,'..','..','adversarial','out')
def hex_of(cells):
    if any(not(-6<=x<=5 and -6<=y<=5) for x,y in cells): return None
    bits=['0']*144
    for x,y in cells: bits[(y+6)*12+(x+6)]='1'
    return '%036x'%int(''.join(bits),2)
S=set(); nB=0; per={}
for name in ('main_seed1','main_seed2','ext_seed11','ext_seed12'):
    n0=len(S); c=0
    with open(os.path.join(od,f'attack_b_{name}.csv')) as f:
        rd=csv.reader(f); next(rd)
        for r in rd: S.add(r[5]); c+=1
    nB+=c; per[name]=dict(rows=c, new_distinct=len(S)-n0)
print('B rows', nB, 'distinct genomes', len(S), 'duplicate evaluations', nB-len(S), per)
A=[tuple(map(tuple,json.loads(l)['cells'])) for l in open(os.path.join(od,'attack_a.jsonl'))]
C=[tuple(map(tuple,json.loads(l)['cells'])) for l in open(os.path.join(od,'attack_c.jsonl'))]
D=json.load(open(os.path.join(od,'attack_d_summary.json'))); cfg=[]; Dc=[]
for s in D['stages']:
    Dc.append(tuple(map(tuple,cfg)))
    if 'obstacle' in s: cfg=cfg+[tuple(c) for c in s['obstacle']]
other=set()
inB=0
for cl in list(A)+list(C)+Dc:
    h=hex_of(cl)
    if h is not None and h in S: inB+=1
    elif h is not None: S.add(h)
    else: other.add(tuple(sorted(cl)))
print('A distinct', len(set(A)), 'C distinct', len(set(C)), 'D chain configs', len(Dc), '(140 D candidate configs are not logged individually)')
print('A/C/D-chain configs already present in B logs:', inB)
print('distinct union of A, C, all B logs, D chain:', len(S)+len(other))
json.dump(dict(B_rows=nB, B_distinct=len(S), per_run=per, union_distinct=len(S)+len(other), ACD_in_B=inB), open(os.path.join(here,'out','check_distinct.json'),'w'), indent=1)
