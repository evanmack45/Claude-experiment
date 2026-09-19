/*
 * randexp.c -- random-initial-configuration test of the Langton's-ant highway
 * conjecture (research/CONVENTIONS.md), across box sizes k and densities p.
 *
 * Usage:
 *   ./randexp run  k p seed nsamples cap outcsv        (append one CSV row per sample)
 *   ./randexp dump k p seed sample_index               (print the configuration as JSON)
 *   ./randexp one  k p seed sample_index cap           (run one sample, print JSON result)
 *   ./randexp stats k p seed nsamples cap outprefix    (aggregate-only: onset list as uint32 + specials + summary)
 *
 * Random configuration (CONVENTIONS.md): every cell (x,y) with
 *   xmin <= x,y <= xmin + k - 1,  xmin = -(k/2)   (integer division: -floor(k/2)
 *   for odd k, -k/2 for even k, i.e. -k/2 <= x,y < k/2 for even k)
 * is black independently with probability p.  The ant starts at (0,0) facing
 * North whatever the colour of the origin.
 *
 * Sampling scheme (deterministic, per sample): the cells are visited in the
 * order i = 0..k*k-1, (x,y) = (xmin + i % k, xmin + i / k).  The RNG is
 * splitmix64 with initial state
 *   z0 = seed*0x9E3779B97F4A7C15 + sample_index*0xBF58476D1CE4E5B9
 *        + k*0x94D049BB133111EB + p1000*0xD6E8FEB86659FD93    (mod 2^64)
 * where p1000 = round(1000*p).  For each cell one 64-bit output r is drawn and
 * the cell is black iff (r >> 11) * 2^-53 < p.  Hence any single sample is
 * reproducible from (k, p, seed, sample_index) alone.
 *
 * Ant rules: white -> turn right (N->E), black -> turn left; flip; move.
 * t[n] = 'R' if step n turned right.  Onset step s = max{ k : t[k] != t[k+104] }
 * (0 if no mismatch ever).  Certification (identical to research/exhaustive/exhaust.c):
 * at step n >= s + 2184 the equalities t[k]==t[k+104] have been verified for all
 * k in s+1..n-104 (>= 20 full periods); the ant must be >= 20 cells beyond the
 * bounding box of {origin, initial black cells, cells modified in steps 1..s}
 * in BOTH coordinates in the direction of travel (sign of pos(n)-pos(n-104),
 * both components nonzero).  Then the run is certified and stopped.
 *
 * Outcomes: certified | cap | boundary | nontravel
 *   cap        : step cap reached without certification
 *   boundary   : ant reached the outermost ring of the 4096x4096 grid (reported,
 *                never silently wrapped)
 *   nontravel  : cap reached while the turn sequence was 104-periodic for >= 20
 *                periods but the displacement per period had a zero component
 *                (or the escape margin was never reached)
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <limits.h>

#define GRID 4096
#define ORIGIN (GRID/2)
#define RING 128
#define RMASK (RING-1)
#define PERIOD 104
#define NPERIODS 20
#define MARGIN 20
#define CERT_LEN (PERIOD + NPERIODS*PERIOD)   /* 2184 */

enum { ST_CERT = 0, ST_CAP = 1, ST_BOUNDARY = 2, ST_NONTRAVEL = 3 };
static const char *STNAME[4] = {"certified", "cap", "boundary", "nontravel"};
static const char *DIRNAME[4] = {"+x,+y", "+x,-y", "-x,+y", "-x,-y"};

static uint8_t *cells;      /* bit0 = colour, bit1 = touched */
static int32_t *touched;    /* indices of touched cells for fast reset */
static long ntouched;

typedef struct {
    int status;
    int64_t s;          /* onset step */
    int64_t steps;      /* steps executed when the run stopped */
    int dispx, dispy;   /* displacement per period at certification */
    int fx, fy;         /* final ant position (relative to origin) */
    int bx0, by0, bx1, by1;  /* bounding box at onset (relative to origin) */
    int dirid;          /* 0:+x,+y 1:+x,-y 2:-x,+y 3:-x,-y */
    int nblack;         /* number of initial black cells */
    int64_t periods_verified; /* full periods verified at stop */
} result_t;

/* ---------- RNG ---------- */
static uint64_t sm_state;
static uint64_t splitmix64(void) {
    uint64_t z = (sm_state += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}
static void seed_sample(int k, double p, uint64_t seed, uint64_t idx) {
    uint64_t p1000 = (uint64_t)llround(1000.0 * p);
    sm_state = seed * 0x9E3779B97F4A7C15ULL + idx * 0xBF58476D1CE4E5B9ULL
             + (uint64_t)k * 0x94D049BB133111EBULL + p1000 * 0xD6E8FEB86659FD93ULL;
}
/* fill config[] (k*k bytes, index i = (x - xmin) + k*(y - xmin)) */
static int gen_config(int k, double p, uint64_t seed, uint64_t idx, uint8_t *config) {
    seed_sample(k, p, seed, idx);
    int nb = 0;
    for (int i = 0; i < k * k; i++) {
        uint64_t r = splitmix64();
        double u = (double)(r >> 11) * (1.0 / 9007199254740992.0);
        config[i] = (u < p);
        nb += config[i];
    }
    return nb;
}

static void run(int k, const uint8_t *config, int64_t cap, result_t *r)
{
    static const int DX[4] = {0, 1, 0, -1};
    static const int DY[4] = {1, 0, -1, 0};
    int xmin = -(k / 2);
    int bx0 = ORIGIN, by0 = ORIGIN, bx1 = ORIGIN, by1 = ORIGIN; /* includes origin */
    ntouched = 0;
    int nblack = 0;
    for (int i = 0; i < k * k; i++) {
        if (config[i]) {
            int cx = ORIGIN + xmin + i % k, cy = ORIGIN + xmin + i / k;
            int32_t idx = cy * GRID + cx;
            cells[idx] = 3;
            touched[ntouched++] = idx;
            nblack++;
            if (cx < bx0) bx0 = cx;
            if (cx > bx1) bx1 = cx;
            if (cy < by0) by0 = cy;
            if (cy > by1) by1 = cy;
        }
    }
    uint8_t tring[RING];
    int32_t rbx0[RING], rby0[RING], rbx1[RING], rby1[RING], rpx[RING], rpy[RING];
    int x = ORIGIN, y = ORIGIN, dir = 0;
    rbx0[0] = bx0; rby0[0] = by0; rbx1[0] = bx1; rby1[0] = by1; rpx[0] = x; rpy[0] = y;
    int sbx0 = bx0, sby0 = by0, sbx1 = bx1, sby1 = by1; /* snapshot bbox at step L */
    int64_t L = 0, n = 0;
    int status = ST_CAP, dispx = 0, dispy = 0;

    while (n < cap) {
        n++;
        int32_t idx = y * GRID + x;
        uint8_t c = cells[idx];
        uint8_t t;
        if (c & 1) { dir = (dir + 3) & 3; t = 0; }   /* black: left */
        else       { dir = (dir + 1) & 3; t = 1; }   /* white: right */
        if (!(c & 2)) touched[ntouched++] = idx;
        cells[idx] = (uint8_t)(2 | ((c & 1) ^ 1));
        if (x < bx0) bx0 = x; else if (x > bx1) bx1 = x;
        if (y < by0) by0 = y; else if (y > by1) by1 = y;
        x += DX[dir]; y += DY[dir];
        if (x <= 0 || x >= GRID - 1 || y <= 0 || y >= GRID - 1) { status = ST_BOUNDARY; break; }
        int ri = (int)(n & RMASK);
        if (n > PERIOD) {
            int pi = (int)((n - PERIOD) & RMASK);
            if (tring[pi] != t) {
                L = n - PERIOD;
                sbx0 = rbx0[pi]; sby0 = rby0[pi]; sbx1 = rbx1[pi]; sby1 = rby1[pi];
            }
        }
        tring[ri] = t;
        rbx0[ri] = bx0; rby0[ri] = by0; rbx1[ri] = bx1; rby1[ri] = by1;
        rpx[ri] = x; rpy[ri] = y;
        if (n >= L + CERT_LEN) {
            int pi = (int)((n - PERIOD) & RMASK);
            dispx = x - rpx[pi]; dispy = y - rpy[pi];
            if (dispx != 0 && dispy != 0) {
                int okx = dispx > 0 ? (x >= sbx1 + MARGIN) : (x <= sbx0 - MARGIN);
                int oky = dispy > 0 ? (y >= sby1 + MARGIN) : (y <= sby0 - MARGIN);
                if (okx && oky) { status = ST_CERT; break; }
            }
        }
    }
    if (status == ST_CAP && n >= L + CERT_LEN) status = ST_NONTRAVEL;
    for (long i = 0; i < ntouched; i++) cells[touched[i]] = 0;

    r->status = status; r->s = L; r->steps = n;
    r->dispx = dispx; r->dispy = dispy;
    r->fx = x - ORIGIN; r->fy = y - ORIGIN;
    r->bx0 = sbx0 - ORIGIN; r->by0 = sby0 - ORIGIN; r->bx1 = sbx1 - ORIGIN; r->by1 = sby1 - ORIGIN;
    r->dirid = (dispx > 0 ? 0 : 2) + (dispy > 0 ? 0 : 1);
    r->nblack = nblack;
    r->periods_verified = (n - PERIOD - L) / PERIOD; if (r->periods_verified < 0) r->periods_verified = 0;
}

static void print_cells(FILE *f, int k, const uint8_t *config) {
    int xmin = -(k / 2), first = 1;
    fputc('[', f);
    for (int i = 0; i < k * k; i++) if (config[i]) {
        fprintf(f, "%s[%d,%d]", first ? "" : ",", xmin + i % k, xmin + i / k);
        first = 0;
    }
    fputc(']', f);
}

static void print_result_json(FILE *f, int k, double p, uint64_t seed, uint64_t idx, const result_t *r, const uint8_t *config, int with_cells) {
    fprintf(f, "{\"k\": %d, \"p\": %g, \"seed\": %llu, \"sample_index\": %llu, \"outcome\": \"%s\", \"onset_step\": %lld, "
               "\"direction\": \"%s\", \"steps_simulated\": %lld, \"n_black\": %d, \"disp\": [%d,%d], \"final_pos\": [%d,%d], "
               "\"bbox_pre_onset\": [%d,%d,%d,%d], \"periods_verified\": %lld",
            k, p, (unsigned long long)seed, (unsigned long long)idx, STNAME[r->status], (long long)r->s,
            r->status == ST_CERT ? DIRNAME[r->dirid] : "none", (long long)r->steps, r->nblack, r->dispx, r->dispy,
            r->fx, r->fy, r->bx0, r->by0, r->bx1, r->by1, (long long)r->periods_verified);
    if (with_cells) { fprintf(f, ", \"black_cells\": "); print_cells(f, k, config); }
    fprintf(f, "}\n");
}

int main(int argc, char **argv)
{
    if (argc < 6) { fprintf(stderr, "usage: %s run k p seed nsamples cap outcsv | dump k p seed idx | one k p seed idx cap\n", argv[0]); return 1; }
    const char *mode = argv[1];
    int k = atoi(argv[2]);
    double p = atof(argv[3]);
    uint64_t seed = strtoull(argv[4], 0, 10);
    if (k < 1 || k > 1024) { fprintf(stderr, "bad k\n"); return 1; }
    uint8_t *config = malloc((size_t)k * k);

    if (!strcmp(mode, "dump")) {
        uint64_t idx = strtoull(argv[5], 0, 10);
        int nb = gen_config(k, p, seed, idx, config);
        printf("{\"k\": %d, \"p\": %g, \"seed\": %llu, \"sample_index\": %llu, \"n_black\": %d, \"black_cells\": ",
               k, p, (unsigned long long)seed, (unsigned long long)idx, nb);
        print_cells(stdout, k, config); printf("}\n");
        return 0;
    }

    cells = calloc((size_t)GRID * GRID, 1);
    touched = malloc(sizeof(int32_t) * ((size_t)GRID * GRID + 16));
    if (!cells || !touched) { fprintf(stderr, "alloc failed\n"); return 1; }

    if (!strcmp(mode, "one")) {
        if (argc < 7) { fprintf(stderr, "one k p seed idx cap\n"); return 1; }
        uint64_t idx = strtoull(argv[5], 0, 10);
        int64_t cap = atoll(argv[6]);
        gen_config(k, p, seed, idx, config);
        result_t r; run(k, config, cap, &r);
        print_result_json(stdout, k, p, seed, idx, &r, config, 1);
        return 0;
    }


    if (!strcmp(mode, "stats")) {
        /* stats k p seed nsamples cap outprefix : aggregate-only mode.
           Writes <outprefix>.u32 (onset step of every certified sample, uint32, sample order),
           <outprefix>_special.txt (one JSON line per non-certified sample, with cells) and
           appends a JSON summary line to <outprefix>_summary.jsonl. */
        if (argc < 8) { fprintf(stderr, "stats k p seed nsamples cap outprefix\n"); return 1; }
        uint64_t nsamples = strtoull(argv[5], 0, 10);
        int64_t cap = atoll(argv[6]);
        const char *pre = argv[7];
        char fn[512];
        snprintf(fn, sizeof fn, "%s.u32", pre); FILE *fu = fopen(fn, "wb");
        snprintf(fn, sizeof fn, "%s_special.txt", pre); FILE *fs = fopen(fn, "w");
        if (!fu || !fs) { fprintf(stderr, "cannot open outputs\n"); return 1; }
        struct timespec t0, t1; clock_gettime(CLOCK_MONOTONIC, &t0);
        int64_t total_steps = 0, ncert = 0, ncap = 0, nbound = 0, nnontr = 0, smax = -1, smin = INT64_MAX;
        double ssum = 0; uint64_t argmax = 0; int64_t dircount[4] = {0,0,0,0}; int64_t n_disp_not_2_2 = 0;
        double nbsum = 0;
        for (uint64_t idx = 0; idx < nsamples; idx++) {
            gen_config(k, p, seed, idx, config);
            result_t r; run(k, config, cap, &r);
            total_steps += r.steps; nbsum += r.nblack;
            if (r.status == ST_CERT) {
                ncert++; ssum += r.s; if (r.s > smax) { smax = r.s; argmax = idx; } if (r.s < smin) smin = r.s;
                uint32_t v = (uint32_t)r.s; fwrite(&v, 4, 1, fu);
                dircount[r.dirid]++;
                if (abs(r.dispx) != 2 || abs(r.dispy) != 2) n_disp_not_2_2++;
            } else {
                if (r.status == ST_CAP) ncap++; else if (r.status == ST_BOUNDARY) nbound++; else nnontr++;
                print_result_json(fs, k, p, seed, idx, &r, config, 1);
            }
        }
        fclose(fu); fclose(fs);
        clock_gettime(CLOCK_MONOTONIC, &t1);
        double el = (t1.tv_sec - t0.tv_sec) + 1e-9 * (t1.tv_nsec - t0.tv_nsec);
        snprintf(fn, sizeof fn, "%s_summary.jsonl", pre); FILE *fj = fopen(fn, "a");
        fprintf(fj, "{\"k\": %d, \"p\": %g, \"seed\": %llu, \"n\": %llu, \"cap\": %lld, \"n_certified\": %lld, \"n_cap\": %lld, \"n_boundary\": %lld, \"n_nontravel\": %lld, "
                    "\"s_min\": %lld, \"s_max\": %lld, \"s_mean\": %.6f, \"argmax_sample_index\": %llu, \"mean_n_black\": %.6f, "
                    "\"dir_counts\": {\"+x,+y\": %lld, \"+x,-y\": %lld, \"-x,+y\": %lld, \"-x,-y\": %lld}, \"n_disp_not_pm2_pm2\": %lld, "
                    "\"total_steps\": %lld, \"elapsed_s\": %.3f}\n",
                k, p, (unsigned long long)seed, (unsigned long long)nsamples, (long long)cap, (long long)ncert, (long long)ncap,
                (long long)nbound, (long long)nnontr, (long long)(ncert ? smin : -1), (long long)smax, ncert ? ssum / ncert : -1.0,
                (unsigned long long)argmax, nbsum / nsamples, (long long)dircount[0], (long long)dircount[1], (long long)dircount[2],
                (long long)dircount[3], (long long)n_disp_not_2_2, (long long)total_steps, el);
        fclose(fj);
        fprintf(stderr, "stats k=%d p=%g seed=%llu n=%llu: cert=%lld cap=%lld boundary=%lld nontravel=%lld smax=%lld (idx %llu) %.1fs %.1f Msteps/s\n",
                k, p, (unsigned long long)seed, (unsigned long long)nsamples, (long long)ncert, (long long)ncap, (long long)nbound,
                (long long)nnontr, (long long)smax, (unsigned long long)argmax, el, total_steps / el / 1e6);
        return 0;
    }

    if (strcmp(mode, "run")) { fprintf(stderr, "unknown mode\n"); return 1; }
    if (argc < 8) { fprintf(stderr, "run k p seed nsamples cap outcsv\n"); return 1; }
    uint64_t nsamples = strtoull(argv[5], 0, 10);
    int64_t cap = atoll(argv[6]);
    const char *outcsv = argv[7];
    FILE *fo = fopen(outcsv, "a");
    if (!fo) { fprintf(stderr, "cannot open %s\n", outcsv); return 1; }

    struct timespec t0, t1; clock_gettime(CLOCK_MONOTONIC, &t0);
    int64_t total_steps = 0, ncert = 0, ncap = 0, nbound = 0, nnontr = 0, smax = -1; uint64_t argmax = 0;
    for (uint64_t idx = 0; idx < nsamples; idx++) {
        gen_config(k, p, seed, idx, config);
        result_t r; run(k, config, cap, &r);
        total_steps += r.steps;
        if (r.status == ST_CERT) { ncert++; if (r.s > smax) { smax = r.s; argmax = idx; } }
        else if (r.status == ST_CAP) ncap++;
        else if (r.status == ST_BOUNDARY) nbound++;
        else nnontr++;
        /* required columns first, then extra detail columns */
        fprintf(fo, "%d,%g,%llu,%llu,%s,%lld,\"%s\",%lld,%d,%d,%d,%d,%d,%d,%d,%d,%d,%lld\n",
                k, p, (unsigned long long)seed, (unsigned long long)idx, STNAME[r.status], (long long)r.s,
                r.status == ST_CERT ? DIRNAME[r.dirid] : "none", (long long)r.steps,
                r.nblack, r.dispx, r.dispy, r.fx, r.fy, r.bx0, r.by0, r.bx1, r.by1, (long long)r.periods_verified);
    }
    fclose(fo);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double el = (t1.tv_sec - t0.tv_sec) + 1e-9 * (t1.tv_nsec - t0.tv_nsec);
    fprintf(stderr, "k=%d p=%g seed=%llu n=%llu: cert=%lld cap=%lld boundary=%lld nontravel=%lld smax=%lld (idx %llu) steps=%lld %.1fs %.1f Msteps/s\n",
            k, p, (unsigned long long)seed, (unsigned long long)nsamples, (long long)ncert, (long long)ncap, (long long)nbound,
            (long long)nnontr, (long long)smax, (unsigned long long)argmax, (long long)total_steps, el, total_steps / el / 1e6);
    return 0;
}
