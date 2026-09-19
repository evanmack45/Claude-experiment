"""Independent (written by the reviewer) brute-force reference for CONVENTIONS.md:
ant at (0,0) facing N=(0,1); white -> right (clockwise), black -> left; flip; move.
onset s = max{k>=1: t[k]!=t[k+104]} over the simulated window; certification as in CONVENTIONS."""
def simulate(black, nsteps):
    g = {c: 1 for c in black}
    heading = (0, 1); pos = (0, 0)
    turns = []; positions = [pos]
    for step in range(1, nsteps + 1):
        c = g.get(pos, 0)
        hx, hy = heading
        if c == 0:
            heading = (hy, -hx)     # right/clockwise: (0,1)->(1,0)->(0,-1)->(-1,0)
            turns.append('R')
        else:
            heading = (-hy, hx)     # left/counter-clockwise: (0,1)->(-1,0)
            turns.append('L')
        g[pos] = 1 - c
        pos = (pos[0] + heading[0], pos[1] + heading[1])
        positions.append(pos)
    return turns, positions

def onset_and_cert(black, nsteps, period=104, nper=20, margin=20):
    turns, P = simulate(black, nsteps)
    t = lambda k: turns[k - 1]
    s = 0
    for k in range(1, nsteps - period + 1):
        if t(k) != t(k + period): s = k
    pts = [(0, 0)] + list(black) + P[:s]        # cells modified in steps 1..s are read at positions P[0..s-1]
    bx0 = min(q[0] for q in pts); bx1 = max(q[0] for q in pts); by0 = min(q[1] for q in pts); by1 = max(q[1] for q in pts)
    cert = None; disp = None
    for n in range(s + period + nper * period, nsteps + 1):
        dx = P[n][0] - P[n - period][0]; dy = P[n][1] - P[n - period][1]
        if dx == 0 or dy == 0: continue
        okx = (P[n][0] >= bx1 + margin) if dx > 0 else (P[n][0] <= bx0 - margin)
        oky = (P[n][1] >= by1 + margin) if dy > 0 else (P[n][1] <= by0 - margin)
        if okx and oky: cert = n; disp = (dx, dy); break
    d = None
    if disp: d = ('+x' if disp[0] > 0 else '-x') + ',' + ('+y' if disp[1] > 0 else '-y')
    return dict(s=s, cert=cert, disp=disp, dir=d, bbox=(bx0, by0, bx1, by1), final=P[cert] if cert else None)
