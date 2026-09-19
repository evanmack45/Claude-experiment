# Shared conventions for all Langton's Ant research in this repo

Every experiment, script, and result in `research/` MUST use these definitions so
that numbers from different agents are directly comparable.

## The system
- Infinite grid Z^2. Each cell is white (0) or black (1). Initially all cells are
  white except an explicitly given finite set of black cells (the "initial configuration").
- The ant starts at the origin (0, 0), facing **North** (direction (0, +1)).
- Directions and right turns: N=(0,+1) -> E=(+1,0) -> S=(0,-1) -> W=(-1,0) -> N.
  A right turn is clockwise (N->E). A left turn is counter-clockwise (N->W).

## One step
1. Read the cell c under the ant.
2. If c is white (0): turn **right**. If c is black (1): turn **left**.
3. Flip the cell (white<->black).
4. Move forward one cell in the new direction.

The step counter n = number of steps executed. After n steps the ant has moved n times.
Step k (k = 1, 2, 3, ...) is the k-th application of the rule.

## Turn sequence
t[k] = 'R' if step k turned right (the cell was white), else 'L'.

## The highway and its onset step
The highway is the 104-step periodic regime. Define the **onset step** s as the
smallest integer s >= 0 such that for every k >= s + 1, t[k] == t[k + 104]
(the turn sequence is 104-periodic from step s+1 onward, forever).

"Forever" must be *certified*, not assumed: report periodicity for at least 20
consecutive periods AND show that the ant has escaped the bounding box of all cells
modified before step s+1 in its direction of travel by a margin of at least 20 cells
in both coordinates (so its future path, a diagonal strip of bounded width, can never
touch any previously modified cell). Report the certification separately from the
onset step.

Report **s** (the number of steps completed before the periodic regime begins), the
period (expected 104), the displacement of the ant per period, and the highway
direction (e.g. "+x,-y").

## Random initial configurations
A "random configuration in a k x k box with density p" means: every cell (x, y) with
-floor(k/2) <= x, y <= floor(k/2) (for odd k) or -k/2 <= x, y < k/2 (for even k) is black
independently with probability p. The ant still starts at (0,0) facing North, whatever
color the origin cell is. Always record the RNG seed and the sampling scheme in results.

## Exhaustive small boxes
"All patterns in a k x k box" means all 2^(k*k) assignments to the cells in the box
defined above, ant at (0,0) facing North.

## Results format
Write machine-readable results to `research/results/<experiment>.json` with a
top-level object containing at least: {"experiment", "conventions": "CONVENTIONS.md",
"parameters", "results", "notes"}. Keep code that produced each result next to it and
make it runnable with one command documented in a README in that directory.
