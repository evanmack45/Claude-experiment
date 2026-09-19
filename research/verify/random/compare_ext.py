#!/usr/bin/env python3
"""Verifier: byte-for-byte comparison of my re-run onset lists (out/{ext,scale,pfine}/*.u32) with the
finder's (research/random/out/{ext,scale,pfine}/*.u32), plus recomputation of C7/C8/C12 numbers from MY lists."""
import glob, os, json, numpy as np
F = '/home/user/Claude-experiment/research/random/out'; V = '/home/user/Claude-experiment/research/verify/random/out'
def median(a):
    a = sorted(a); n = len(a); return a[n//2] if n % 2 else (a[n//2-1] + a[n//2]) / 2
tot = 0; same = 0; total_n = 0; allsum = {}
for sub in ('ext', 'scale', 'pfine'):
    for fn in sorted(glob.glob(os.path.join(V, sub, '*.u32'))):
        base = os.path.basename(fn); mine = open(fn, 'rb').read(); theirs = open(os.path.join(F, sub, base), 'rb').read()
        tot += 1; same += (mine == theirs); total_n += len(mine) // 4
        if mine != theirs: print('DIFFER', sub, base, len(mine)//4, len(theirs)//4)
    for fn in glob.glob(os.path.join(V, sub, '*_summary.jsonl')):
        for line in open(fn): s = json.loads(line); allsum[(sub, s['k'], s['p'])] = s
print('u32 files compared: %d, identical: %d, total certified onsets in my lists: %d' % (tot, same, total_n))
print('my summaries: cells %d, sum n %d, sum certified %d, max |coord| any step %d, max steps single run %d' % (
    len(allsum), sum(s['n'] for s in allsum.values()), sum(s['n_certified'] for s in allsum.values()),
    max(s['max_abs_coord_all_steps'] for s in allsum.values()), max(s['max_steps_single_run'] for s in allsum.values())))
print('my n_disp_not_pm2_pm2 total:', sum(s['n_disp_not_pm2_pm2'] for s in allsum.values()))
sc = {int(os.path.basename(f)[1:-4]): np.fromfile(f, dtype=np.uint32).astype(np.int64).tolist() for f in glob.glob(os.path.join(V, 'scale', '*.u32'))}
ks = sorted(sc); meds = [median(sc[k]) for k in ks]
print('C7 (mine): k', ks); print('   medians', meds); print('   max', [max(sc[k]) for k in ks], 'argmax k512', sc[512].index(max(sc[512])))
big = [k for k in ks if k >= 64]; bm = [m for k, m in zip(ks, meds) if k >= 64]
lx, ly = np.log(np.array(big, float)), np.log(np.array(bm))
b = ((lx-lx.mean())*(ly-ly.mean())).sum()/((lx-lx.mean())**2).sum(); a = ly.mean() - b*lx.mean()
r2 = 1 - ((ly-(a+b*lx))**2).sum()/((ly-ly.mean())**2).sum()
print('C7 (mine): exponent k>=64 %.4f r2 %.4f ; N-exponent %.4f' % (b, r2, b/2))
ext = {os.path.basename(f)[:-4]: np.fromfile(f, dtype=np.uint32).astype(np.int64).tolist() for f in glob.glob(os.path.join(V, 'ext', '*.u32'))}
bb = max(ext, key=lambda x: max(ext[x])); print('C8 (mine): ext longest', max(ext[bb]), 'cell', bb, 'idx', ext[bb].index(max(ext[bb])), 'ext total', sum(len(v) for v in ext.values()))
pf = {float(os.path.basename(f)[1:-4]): np.fromfile(f, dtype=np.uint32).astype(np.int64).tolist() for f in glob.glob(os.path.join(V, 'pfine', '*.u32'))}
ps = sorted(pf); print('C12 (mine): p', ps); print('    medians', [median(pf[p]) for p in ps], 'total', sum(len(pf[p]) for p in ps))
