/*
 * ant.c -- Langton's Ant simulator following research/CONVENTIONS.md
 *
 *   grid: white=0 / black=1, ant starts at (0,0) facing North (0,+1).
 *   step: read cell; white -> turn Right (clockwise), black -> turn Left;
 *         flip cell; move forward one cell.
 *   t[k] = 'R' if step k turned right, 'L' otherwise (k = 1..N).
 *
 * Usage:  ./ant N OUTDIR
 *
 * Writes to OUTDIR:
 *   turns.txt      the turn string t[1..N] (one line, N chars)
 *   traj.txt       N+1 lines "x y d" = ant position/direction after step 0..N
 *                  (d: 0=N,1=E,2=S,3=W)
 *   onset.txt      key=value lines: s (CONVENTIONS onset), certification data,
 *                  pre-onset statistics
 *   black_s.txt        black cells after step s          (one "x y" per line)
 *   black_s2080.txt    black cells after step s+2080     (one "x y" per line)
 *   black_s1040.txt    black cells after step s+1040
 *   modified_pre.txt   cells modified at steps 1..s (the set whose bbox certifies)
 *
 * Coordinates: x to the East, y to the North (CONVENTIONS).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

/* Grid side G is chosen at runtime from N: the ant can move at most N cells,
 * but the highway advances only 2 cells per 104 steps, so G = 2*(2N/104)+512
 * is ample (the pre-onset chaos stays within ~50 cells of the origin).
 * Origin sits at index (OFF, OFF), OFF = G/2. Bounds are guarded every step. */
static int G, OFF;
static unsigned char *grid;   /* grid[(x+OFF)*G + (y+OFF)] */
static unsigned char *mark;
#define CELL(x,y) grid[((x)+OFF)*(long)G + ((y)+OFF)]
#define MARK(x,y) mark[((x)+OFF)*(long)G + ((y)+OFF)]

static const int DX[4] = {0, 1, 0, -1};   /* N E S W */
static const int DY[4] = {1, 0, -1, 0};

static int32_t *PX, *PY;
static int8_t  *PD;
static char    *T;

static void die(const char *m) { fprintf(stderr, "%s\n", m); exit(1); }

/* simulate n steps from empty grid; record turns/positions if arrays given */
static void simulate(long n, int record) {
    memset(grid, 0, (size_t)G * G);
    int x = 0, y = 0, d = 0;
    if (record) { PX[0] = 0; PY[0] = 0; PD[0] = 0; }
    for (long k = 1; k <= n; k++) {
        if (x <= -OFF || x >= OFF - 1 || y <= -OFF || y >= OFF - 1) { fprintf(stderr,"bounds at k=%ld x=%d y=%d\n",k,x,y); die("grid bounds exceeded"); };
        unsigned char *c = &CELL(x, y);
        if (*c == 0) { d = (d + 1) & 3; if (record) T[k] = 'R'; }
        else         { d = (d + 3) & 3; if (record) T[k] = 'L'; }
        *c ^= 1;
        x += DX[d]; y += DY[d];
        if (record) { PX[k] = x; PY[k] = y; PD[k] = d; }
    }
}

static void dump_black(const char *path) {
    FILE *f = fopen(path, "w"); if (!f) die("open fail");
    for (int i = 0; i < G; i++) for (int j = 0; j < G; j++)
        if (grid[(long)i * G + j]) fprintf(f, "%d %d\n", i - OFF, j - OFF);
    fclose(f);
}

static long count_black(void) {
    long c = 0;
    for (long i = 0; i < (long)G * G; i++) c += grid[i];
    return c;
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: ant N OUTDIR\n"); return 1; }
    long N = atol(argv[1]);
    const char *out = argv[2];
    char path[1024];

    G = 2 * (int)(2 * N / 104) + 512; OFF = G / 2;
    grid = malloc((size_t)G * G); mark = malloc((size_t)G * G);
    if (!grid || !mark) die("alloc grid");
    fprintf(stderr, "grid %dx%d\n", G, G);
    PX = malloc((N + 1) * sizeof *PX); PY = malloc((N + 1) * sizeof *PY);
    PD = malloc((N + 1) * sizeof *PD); T = malloc(N + 2);
    if (!PX || !PY || !PD || !T) die("alloc");

    simulate(N, 1);
    T[0] = '?'; T[N + 1] = 0;

    /* ---- onset step s per CONVENTIONS: smallest s with t[k]==t[k+104] for all k>=s+1 (k+104<=N) */
    long P = 104;
    long s = 0;
    for (long k = N - P; k >= 1; k--) if (T[k] != T[k + P]) { s = k; break; }

    /* alternative: state periodicity (pos difference & dir), smallest k with
       PX[j+104]-PX[j]==DXp etc for all j>=k */
    long DXp = PX[N] - PX[N - P], DYp = PY[N] - PY[N - P];
    long s_state = 0;
    for (long j = N - P; j >= 0; j--)
        if (PX[j + P] - PX[j] != DXp || PY[j + P] - PY[j] != DYp || PD[j + P] != PD[j]) { s_state = j + 1; break; }

    /* ---- pre-onset statistics ----
       modified-before-step-(s+1) cells = positions PX[0..s-1] (cell read at step k is position after k-1)
       visited cells through step s = positions PX[0..s]                                       */
    memset(mark, 0, (size_t)G * G);
    long nmod = 0; int minx = 0, maxx = 0, miny = 0, maxy = 0;
    for (long k = 0; k < s; k++) {
        if (!MARK(PX[k], PY[k])) { MARK(PX[k], PY[k]) = 1; nmod++; }
        if (PX[k] < minx) minx = PX[k];
        if (PX[k] > maxx) maxx = PX[k];
        if (PY[k] < miny) miny = PY[k];
        if (PY[k] > maxy) maxy = PY[k];
    }
    snprintf(path, sizeof path, "%s/modified_pre.txt", out);
    { FILE *f = fopen(path, "w");
      for (int i = 0; i < G; i++) for (int j = 0; j < G; j++) if (mark[(long)i * G + j]) fprintf(f, "%d %d\n", i - OFF, j - OFF);
      fclose(f); }
    long nvis = nmod; if (!MARK(PX[s], PY[s])) { MARK(PX[s], PY[s]) = 1; nvis++; }
    int vminx = minx, vmaxx = maxx, vminy = miny, vmaxy = maxy;
    if (PX[s] < vminx) vminx = PX[s];
    if (PX[s] > vmaxx) vmaxx = PX[s];
    if (PY[s] < vminy) vminy = PY[s];
    if (PY[s] > vmaxy) vmaxy = PY[s];
    double maxr2 = 0; long maxcheb = 0, maxman = 0, argmax = 0;
    for (long k = 0; k <= s; k++) {
        double r2 = (double)PX[k] * PX[k] + (double)PY[k] * PY[k];
        if (r2 > maxr2) { maxr2 = r2; argmax = k; }
        long cx = labs(PX[k]), cy = labs(PY[k]);
        if (cx > maxcheb) maxcheb = cx;
        if (cy > maxcheb) maxcheb = cy;
        if (cx + cy > maxman) maxman = cx + cy;
    }
    /* last step k at which the ant reads a cell that was modified before step s+1 (revisit of chaos-era cell) */
    memset(mark, 0, (size_t)G * G);
    for (long k = 0; k < s; k++) MARK(PX[k], PY[k]) = 1;
    long last_old = 0;
    for (long k = N; k >= 1; k--) if (MARK(PX[k - 1], PY[k - 1])) { last_old = k; break; }
    /* first step k >= s+1 whose cell (PX[k-1]) is outside the modified-pre set and after which every cell read is new
       (i.e. min k such that for all j>=k, PX[j-1] not in modified-pre) = last_old + 1 */

    /* escape margin: first step m >= s such that ant position is >= 20 cells beyond bbox in the travel direction
       (both coordinates), i.e. sign(DXp)*(x - bbox edge) >= 20 and same for y */
    long m20 = -1, m0 = -1;
    for (long k = s; k <= N; k++) {
        long mx = DXp > 0 ? PX[k] - maxx : minx - PX[k];
        long my = DYp > 0 ? PY[k] - maxy : miny - PY[k];
        if (m0 < 0 && mx >= 1 && my >= 1) m0 = k;
        if (mx >= 20 && my >= 20) { m20 = k; break; }
    }
    /* periods verified: number of full periods with exact 104-periodicity after s within N */
    long periods_verified = (N - s) / P - 1;   /* pairs (k, k+104) checked for k in s+1..N-104 => (N-104-s)/104 periods */
    periods_verified = (N - P - s) / P;

    snprintf(path, sizeof path, "%s/onset.txt", out);
    FILE *f = fopen(path, "w");
    fprintf(f, "N=%ld\nperiod=%ld\ns=%ld\ns_state=%ld\n", N, P, s, s_state);
    fprintf(f, "disp_dx=%ld\ndisp_dy=%ld\n", DXp, DYp);
    fprintf(f, "ant_x_at_s=%d\nant_y_at_s=%d\nant_dir_at_s=%d\n", PX[s], PY[s], PD[s]);
    fprintf(f, "bbox_modified_pre_onset=%d %d %d %d\n", minx, maxx, miny, maxy);
    fprintf(f, "bbox_visited_through_s=%d %d %d %d\n", vminx, vmaxx, vminy, vmaxy);
    fprintf(f, "n_modified_pre_onset=%ld\nn_visited_through_s=%ld\n", nmod, nvis);
    fprintf(f, "max_euclid_dist_through_s=%.6f\nargmax_step=%ld\nmax_cheb_through_s=%ld\nmax_manhattan_through_s=%ld\n",
            sqrt(maxr2), argmax, maxcheb, maxman);
    fprintf(f, "last_step_reading_chaos_cell=%ld\n", last_old);
    fprintf(f, "escape_step_margin1=%ld\nescape_step_margin20=%ld\n", m0, m20);
    fprintf(f, "periods_verified=%ld\n", periods_verified);
    /* count mismatches over the whole checked range after s (must be 0) */
    long mism = 0; for (long k = s + 1; k + P <= N; k++) if (T[k] != T[k + P]) mism++;
    fprintf(f, "mismatches_after_s=%ld\n", mism);
    fprintf(f, "t_s=%c\nt_s_plus_104=%c\n", T[s], T[s + P]);
    fclose(f);

    snprintf(path, sizeof path, "%s/turns.txt", out);
    f = fopen(path, "w"); fwrite(T + 1, 1, N, f); fputc('\n', f); fclose(f);
    snprintf(path, sizeof path, "%s/traj.txt", out);
    f = fopen(path, "w"); for (long k = 0; k <= N; k++) fprintf(f, "%d %d %d\n", PX[k], PY[k], PD[k]); fclose(f);

    /* ---- grid snapshots (re-simulate; cheap) ---- */
    long snaps[3] = {s, s + 1040, s + 2080};
    const char *names[3] = {"black_s.txt", "black_s1040.txt", "black_s2080.txt"};
    snprintf(path, sizeof path, "%s/onset.txt", out);
    f = fopen(path, "a");
    for (int i = 0; i < 3; i++) {
        simulate(snaps[i], 0);
        snprintf(path, sizeof path, "%s/%s", out, names[i]);
        dump_black(path);
        fprintf(f, "black_at_%s=%ld\n", i == 0 ? "s" : (i == 1 ? "s1040" : "s2080"), count_black());
    }
    fclose(f);
    return 0;
}
