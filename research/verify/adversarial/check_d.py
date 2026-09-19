#!/usr/bin/env python3
"""Independent re-implementation of Attack D's greedy 2x2-obstacle chaining (box |x|,|y|<=300) using ./vsim
and my own Python trajectory code; compares candidate counts, chosen obstacles and stage onsets with the
finder's out/attack_d.jsonl, and re-simulates every stage prefix of out/attack_d_final.cfg."""
import json, os, subprocess
here=os.path.dirname(os.path.abspath(__file__)); B=300
theirs=[json.loads(l) for l in open(os.path.join(here,'..','..','adversarial','out','attack_d.jsonl'))]
def sim(cfgs):
    inp='\n'.join(' '.join(f'{x} {y}' for x,y in c) for c in cfgs)+'\n'
    return [json.loads(l) for l in subprocess.run([os.path.join(here,'vsim'),'batch'], input=inp, capture_output=True, text=True).stdout.strip().split('\n')]
def traj(cfg, N):
    black=set(cfg); read=set(cfg); x=y=d=0; pos=[(0,0)]; DX=[0,1,0,-1]; DY=[1,0,-1,0]
    for k in range(N):
        if (x,y) in black: d=(d-1)%4; black.remove((x,y))
        else: d=(d+1)%4; black.add((x,y))
        read.add((x,y)); x+=DX[d]; y+=DY[d]; pos.append((x,y))
    return pos, read
cfg=[]; nsims=0; stage=0
while True:
    r=sim([cfg])[0]; nsims+=1; assert r['outcome']=='certified'
    c=r['cert_step']; disp=r['disp']; pos,read=traj(cfg, c+104)
    cands=[]
    for i in range(0,104,3):
        bx,by=pos[c+i]
        for m in range(400):
            ax,ay=bx+m*disp[0], by+m*disp[1]; cells=[(ax,ay),(ax+1,ay),(ax,ay+1),(ax+1,ay+1)]
            if any(abs(cx)>B or abs(cy)>B for cx,cy in cells): break
            if any(cl in read for cl in cells): continue
            cands.append((i,m,cells)); break
    if not cands:
        print(f'stage {stage}: onset {r["onset"]} dir {r["direction"]} cert {c} -> no candidate fits in box (theirs: {theirs[stage].get("note")})'); break
    rs=sim([cfg+cl for _,_,cl in cands]); nsims+=len(cands)
    ok=[(o,cd) for o,cd in zip(rs,cands) if o['outcome']=='certified' and o['contact']>0]
    best=max(ok, key=lambda oc: oc[0]['onset'])
    th=theirs[stage]
    print(f'stage {stage}: prev onset {r["onset"]} (theirs {th["prev_onset"]}) cert {c} (theirs {th["prev_cert_step"]}) cands {len(cands)} (theirs {th["n_candidates"]}) cert {len(ok)} '
          f'min {min(o["onset"] for o,_ in ok)} (theirs {th["candidate_onsets_min"]}) chosen phase {best[1][0]} m {best[1][1]} cells {best[1][2]} (theirs {th["chosen_phase"]},{th["chosen_periods_ahead"]},{th["obstacle"]}) '
          f'new onset {best[0]["onset"]} (theirs {th["new_onset"]}) contact {best[0]["contact"]} (theirs {th["contact_step"]}) dir {best[0]["direction"]} (theirs {th["new_direction"]})')
    same = (len(cands)==th['n_candidates'] and [list(c) for c in best[1][2]]==th['obstacle'] and best[0]['onset']==th['new_onset'] and best[0]['contact']==th['contact_step'] and best[0]['direction']==th['new_direction'] and min(o['onset'] for o,_ in ok)==th['candidate_onsets_min'])
    print('   stage matches finder:', same)
    cfg=cfg+best[1][2]; stage+=1
final=sim([cfg])[0]; nsims+=1
print('final', final, 'ncells', len(cfg), 'ratio %.4f'%(final['onset']/9977))
print('total simulations in my re-run of D:', nsims)
fc=[tuple(map(int,l.split())) for l in open(os.path.join(here,'..','..','adversarial','out','attack_d_final.cfg')) if not l.startswith('#')]
print('final cfg identical to finder file:', fc==cfg)
print('stage prefixes:', [o['onset'] for o in sim([fc[:4*k] for k in range(1,5)])])
