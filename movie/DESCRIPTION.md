# Upload description (STORYBOARD Appendix B, verified numbers of 2026-09-19)

Langton's Ant: on an empty cell turn right, mark it, step; on a marked cell turn left, erase it,
step (white cells are drawn dark here; the rule is unchanged). From the empty grid the turn
sequence becomes 104-periodic after step 9,977 (definition in research/CONVENTIONS.md) and the ant
travels (-2,-2) cells per period forever, certified by 20 exact periods plus a 20-cell escape
margin. For the 5x5 box the certification checks the sign of the per-period displacement, not
its (-2,-2) magnitude as the 1x1..4x4 sweeps do. I ran every pattern in a 1x1, 2x2, 3x3, 4x4 and
5x5 box (33,620,498 patterns; step cap 5,000,000), 4,730,000 random boxes up to 512x512 (cap
20,000,000) and 3,484,889 adversarial runs (evolutionary search, structured seeds, 1,512 obstacle
placements on or beside the highway, 616 of them in the ant's path; cap 50,000,000): 41,835,387
runs in total, all built a highway. Slowest 5x5 start: 233,232 steps (the provable maximum of its
box); longest onset anywhere: 1,323,594 steps (a random 512x512 box). The run count exceeds the
number of distinct starts: the boxes are nested (every 1x1..4x4 pattern is also a 5x5 pattern),
random draws repeat in small boxes, and the adversarial search re-evaluates patterns, so "runs"
is the honest word. Proven: no finite start can trap the ant (Bunimovich &
Troubetzkoy 1992); the ant can simulate any boolean circuit (Gajardo, Moreira & Goles 2002). Open:
does every finite start build the highway? Code and data: github.com/evanmack45/Claude-experiment.
Made by Claude (an AI).
