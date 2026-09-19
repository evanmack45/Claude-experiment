#!/usr/bin/env python3
"""Re-simulate all Attack-C configurations (cells taken from the finder's out/attack_c.jsonl) with ./vsim and
compare onset/direction/outcome per config; independently regenerate a few named families to check the
cell lists (concentric_rings_13, filled_square_30, diamond_5, vline_21, filled_square_4, single_1_-1)."""
import json, subprocess, os
here=os.path.dirname(os.path.abspath(__file__)); rows=[json.loads(l) for l in open(os.path.join(here,'..','..','adversarial','out','attack_c.jsonl'))]
print('n configs', len(rows), 'distinct names', len(set(r['name'] for r in rows)))
inp='\n'.join(' '.join(f'{c[0]} {c[1]}' for c in r['cells']) for r in rows)+'\n'
out=[json.loads(l) for l in subprocess.run([os.path.join(here,'vsim'),'batch'], input=inp, capture_output=True, text=True).stdout.strip().split('\n')]
assert len(out)==len(rows)
mism=[(r['name'],r['onset_step'],o) for r,o in zip(rows,out) if o['outcome']!='certified' or o['onset']!=r['onset_step'] or o['direction']!=r['direction']]
print('mismatches', len(mism), mism[:5])
top=sorted(zip(rows,out), key=lambda ro: -ro[1]['onset'])[:12]
for r,o in top: print(r['name'], r['family'], o['onset'], o['direction'], 'ncells', len(r['cells']))
byname={r['name']:(r,o) for r,o in zip(rows,out)}
for nm in ('filled_square_4','single_1_-1','empty','best_k5_exhaustive','best_k4_exhaustive'): print(nm, byname[nm][1]['onset'])
# independent regeneration of a few families
def sq(n): lo=-(n//2); return sorted({(x,y) for x in range(lo,lo+n) for y in range(lo,lo+n)})
gen={'concentric_rings_13': sorted({(x,y) for x in range(-6,7) for y in range(-6,7) if max(abs(x),abs(y))%2==0}),
     'filled_square_30': sq(30), 'filled_square_4': sq(4), 'diamond_5': sorted({(x,y) for x in range(-2,3) for y in range(-2,3) if abs(x)+abs(y)<=2}),
     'vline_21': [(0,i) for i in range(21)], 'single_1_-1': [(1,-1)]}
for nm,cells in gen.items(): print(nm, 'cells match finder:', [list(c) for c in cells]==byname[nm][0]['cells'], 'onset', byname[nm][1]['onset'])
nonref=[(r,o) for r,o in zip(rows,out) if r['family']!='reference']
b=max(nonref,key=lambda ro: ro[1]['onset']); print('longest non-reference:', b[0]['name'], b[1]['onset'])
print('all certified', all(o['outcome']=='certified' for o in out))
