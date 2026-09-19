# Two Rules, One Road

**Langton's Ant and the Highway Conjecture: a computational investigation and a short film.**

Video: [`movie/langtons_ant.mp4`](movie/langtons_ant.mp4) (1080x1920 vertical, 79 s, H.264 + AAC, works muted).
Upload text: [`movie/DESCRIPTION.md`](movie/DESCRIPTION.md).
Full research write-up: [`research/FINDINGS.md`](research/FINDINGS.md).

## The mystery

An ant stands on an infinite grid of white cells and follows two rules:

* on a **white** cell: turn right, flip the cell to black, step forward;
* on a **black** cell: turn left, flip the cell to white, step forward.

Started on an empty grid it scribbles what looks like random noise for exactly **9,977 steps**,
then abruptly starts repeating a **104-step cycle** that carries it diagonally to infinity: the
"highway". Every finite starting pattern anyone has ever tried ends the same way.

* **Proven** (Bunimovich and Troubetzkoy, 1992): from any finite start the ant's path is unbounded.
  No finite pattern can trap it.
* **Proven** (Gajardo, Moreira and Goles, 2002): a single ant on a finite pattern can evaluate any
  boolean circuit, so predicting it is P-hard.
* **Open**: does *every* finite starting pattern eventually build the highway? Nobody has proved
  it or found a counterexample in forty years.

## What we established

All simulators are C (about 100 million steps per second), and every number below was re-derived
by an independent verifier who wrote their own simulator from [`research/CONVENTIONS.md`](research/CONVENTIONS.md).
A highway is only counted when its 104-periodicity holds for 20 full periods **and** the ant has
escaped the bounding box of everything it ever touched by 20 cells in its direction of travel.

| Experiment | Runs | Highways | Longest delay before the highway |
|---|---:|---:|---:|
| Every pattern in a 1x1, 2x2, 3x3, 4x4 and 5x5 box | 33,620,498 | 33,620,498 | 233,232 steps (11 cells, provably the 5x5 maximum) |
| Random boxes, 5x5 up to 512x512, densities 0.05 to 0.95 | 4,730,000 | 4,730,000 | 1,323,594 steps (512x512 box, 130,511 black cells) |
| Adversarial: evolutionary search, 202 structured seeds, 1,512 walls dropped on the road | 3,484,889 | 3,484,889 | 259,274 steps (four 2x2 walls, 16 cells) |
| **Total** | **41,835,387** | **41,835,387** | **0 exceptions** |

Other facts the film uses, all verified:

* Empty grid: onset step 9,977; the highway moves (-2, -2) cells per 104 steps; each cycle has
  58 right and 46 left turns and leaves 12 black cells behind.
* The chaos blob before the highway touches 1,376 cells (715 black) inside a 49x45 box.
* A 5x5 pattern exists that is on the highway after only **32 steps**; the most common onset
  among all 33,554,432 patterns in that box is step 266.
* 67.4 % of random starting boxes reach the highway *sooner* than the empty grid.
* Median onset in a random box grows only about linearly with the box side (k^1.14), so the
  ant crosses random media almost ballistically rather than diffusively.
* Every one of the 616 walls that actually hit the highway caused a new highway to form.

This is evidence, not proof: finite enumeration cannot settle a statement about infinitely many
patterns. See [`research/FINDINGS.md`](research/FINDINGS.md) section 4 for the limits.

## Repository layout

```
research/
  CONVENTIONS.md      shared definitions (coordinates, step counting, onset, certification)
  FINDINGS.md         synthesis of all results with citations and reproduction commands
  onset/              exact onset from the empty grid (C + Python cross-check)
  exhaustive/         every pattern in boxes up to 5x5
  random/             random sweeps up to 512x512
  adversarial/        obstacles, evolutionary search, structured seeds, chained walls
  literature/         sources and what is actually proven (SOURCES.md)
  verify/             independent re-implementations by the verifier agents
  results/            machine-readable results; movie_facts.json is the film's only number source
movie/
  STORYBOARD.md       the spec the film was built from
  core.py, common.py  simulation, camera, text, charts, ffmpeg, audio primitives
  scenes_road.py      hook, rules, chaos, freeze, road, infinity, call to action
  scenes_evidence.py  mystery, mosaic, dot wall, stubbornest start, walls, verdict, scorecard
  audio.py            sonification: the ant's own turn sequence read as a waveform
  render.py           frame loop and CLI
  langtons_ant.mp4    the film
```

## Reproduce

Research (see `research/FINDINGS.md` section 6 for one command per result):

```
cd research/onset && make all                 # onset 9977 and the highway geometry, seconds
sh research/exhaustive/run_all.sh             # every 1x1..5x5 pattern, ~17 min on 2 cores
sh research/random/run_all.sh                 # 400,000-box main sweep
sh research/adversarial/run_all.sh            # obstacles, structured seeds, hill-climb
```

Film (Python 3.11, `pip install numpy pillow imageio-ffmpeg`):

```
cd movie && export PYTHONPATH=$PWD
python3 render.py --facts ../research/results/movie_facts.json \
    --out build/silent.mp4 --timeline build/timeline.json
python3 audio.py --timeline build/timeline.json --wav build/mix.wav \
    --mux build/silent.mp4 --out langtons_ant.mp4
```

The renderer aborts if any number it is asked to show is missing from `movie_facts.json` or if
its own re-simulation disagrees with the recorded onset steps.

## How this was made

Everything here was produced by Claude (an AI) in one session, using multi-agent workflows:
five research agents each attacked the problem from a different angle, skeptical verifier
agents re-implemented every simulator from the conventions file and re-derived every claim, a
synthesis agent wrote the findings, a panel of three storyboard proposals was scored by three
judges, engineers built the renderer from the winning storyboard, and reviewers checked the
film frame by frame for legibility, timing and scientific honesty before each fix round.

## Sound

The film's soundtrack is the ant. The sequence of right and left turns is read as a waveform at
22,880 turns per second, so chaos sounds like crackle and the 104-step highway becomes a steady
220 Hz tone. When the road forms, you can hear it.
