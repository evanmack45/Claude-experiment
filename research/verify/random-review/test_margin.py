#!/usr/bin/env python3
"""Soundness of the 20-cell escape margin: on the certified empty-grid highway (direction -x,-y),
measure how far the ant ever moves AGAINST its travel direction within a period, relative to the
position at which the certification test is evaluated. If that excursion is < 20 in both coordinates,
an ant that is >= 20 cells beyond the pre-onset bbox can never re-enter it."""
from ref_ant import simulate
turns, P = simulate(set(), 40000)
s = 9977
mx = my = 0
for n in range(s + 2184, 39000):
    for j in range(1, 105):
        mx = max(mx, P[n + j][0] - P[n][0])   # travel is -x: backward = +x
        my = max(my, P[n + j][1] - P[n][1])   # travel is -y: backward = +y
print('max backward excursion within a period after certification: dx=%d dy=%d (margin is 20)' % (mx, my))
# width of the highway strip: extent perpendicular over a period
xs = [P[n][0] for n in range(20000, 20104)]; ys = [P[n][1] for n in range(20000, 20104)]
print('extent of ant positions over one period: x %d..%d, y %d..%d' % (min(xs), max(xs), min(ys), max(ys)))
